from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from shared.database import get_db
from shared.models import Room, RoomMember, User, UserRole, RoomMemberStatus
from shared.schemas import RoomCreate, RoomResponse, InviteCreate, InvitationResponse, UserResponse
from shared.dependencies import get_current_user

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(room: RoomCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(status_code=403, detail="Only TEACHER can create rooms")
    
    new_room = Room(
        name=room.name,
        description=room.description,
        is_online=room.is_online,
        max_participants=room.max_participants,
        owner_id=current_user.id
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    
    return new_room

@router.get("/", response_model=List[RoomResponse])
def list_rooms(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Rooms owned by user
    owned_rooms = db.query(Room).filter(Room.owner_id == current_user.id).all()
    
    # 2. Rooms where user is a JOINED member
    joined_memberships = db.query(RoomMember).filter(
        RoomMember.user_id == current_user.id,
        RoomMember.status == RoomMemberStatus.JOINED
    ).all()
    joined_rooms = [m.room for m in joined_memberships]
    
    all_rooms = list(set(owned_rooms + joined_rooms))
    
    # Decorate with custom fields
    results = []
    for r in all_rooms:
        role = "OWNER" if r.owner_id == current_user.id else "MEMBER"
        # Monkey patch for response model
        r.role_in_room = role
        r.active_users_count = 0 # Placeholder for Redis/Fusion integration later
        results.append(r)
        
    return results

@router.get("/invitations", response_model=List[InvitationResponse])
def list_invitations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    invites = db.query(RoomMember).filter(
        RoomMember.user_id == current_user.id,
        RoomMember.status == RoomMemberStatus.INVITED
    ).all()
    
    results = []
    for inv in invites:
        results.append({
            "room_id": inv.room_id,
            "room_name": inv.room.name,
            "invited_by": inv.room.owner.username,
            "status": inv.status
        })
    return results

@router.post("/{room_id}/invite")
def invite_user(
    room_id: str, 
    invite: InviteCreate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    try:
        room_uid = uuid.UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Room ID format")

    room = db.query(Room).filter(Room.id == room_uid).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    if room.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the room OWNER can invite members")
    
    target_user = db.query(User).filter(User.username == invite.username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User to invite not found")
        
    # Check if already member/invited
    existing = db.query(RoomMember).filter(RoomMember.room_id == room_uid, RoomMember.user_id == target_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already invited or joined")
        
    new_member = RoomMember(
        room_id=room_uid,
        user_id=target_user.id,
        status=RoomMemberStatus.INVITED,
        permissions=invite.permissions
    )
    db.add(new_member)
    db.commit()
    
    return {"message": f"Invitation sent to {invite.username}"}

@router.post("/{room_id}/join")
def join_room(room_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        room_uid = uuid.UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Room ID format")

    member = db.query(RoomMember).filter(
        RoomMember.room_id == room_uid, 
        RoomMember.user_id == current_user.id,
        RoomMember.status == RoomMemberStatus.INVITED
    ).first()
    
    if not member:
        # Check if they are owner? Owner doesn't need to join.
        room = db.query(Room).filter(Room.id == room_uid).first()
        if room and room.owner_id == current_user.id:
             return {"message": "You are the owner of this room"}
        raise HTTPException(status_code=400, detail="No pending invitation found for this room")
        
    member.status = RoomMemberStatus.JOINED
    db.commit()
    
    return {"message": "You have joined the room"}

@router.put("/{room_id}/status")
def update_room_status(
    room_id: str, 
    is_online: bool, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    try:
        room_uid = uuid.UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Room ID format")

    room = db.query(Room).filter(Room.id == room_uid).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    if room.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the room OWNER can change status")
        
    room.is_online = is_online
    db.commit()
    
    return {"status": "updated", "is_online": is_online}

@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: str, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    try:
        room_uid = uuid.UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Room ID format")

    room = db.query(Room).filter(Room.id == room_uid).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    if room.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the room OWNER can delete it")

    # Cascade delete members (if not handled by DB FK)
    db.query(RoomMember).filter(RoomMember.room_id == room_uid).delete()
    db.delete(room)
    db.commit()
    return None

@router.get("/users/available", response_model=List[UserResponse])
def get_available_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.id != current_user.id).all()
    return users
