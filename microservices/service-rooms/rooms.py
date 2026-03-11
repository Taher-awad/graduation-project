from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_
from typing import List
import uuid

from shared.database import get_db
from shared.models import Room, RoomMember, User, UserRole, RoomMemberStatus
from shared.schemas import RoomCreate, RoomResponse, InviteCreate, InvitationResponse
from shared.dependencies import get_current_user

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(room: RoomCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Only STAFF can create rooms")
    
    new_room = Room(
        name=room.name,
        description=room.description,
        is_online=room.is_online,
        max_participants=room.max_participants,
        owner_id=current_user.id
    )
    db.add(new_room)
    await db.commit()
    await db.refresh(new_room)
    
    return new_room

@router.get("/", response_model=List[RoomResponse])
async def list_rooms(skip: int = 0, limit: int = 50, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Optimized query
    stmt = select(Room).outerjoin(RoomMember, Room.id == RoomMember.room_id).filter(
        or_(
            Room.owner_id == current_user.id,
            (RoomMember.user_id == current_user.id) & (RoomMember.status == RoomMemberStatus.JOINED)
        )
    ).distinct().offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    all_rooms = result.scalars().all()
    
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
async def list_invitations(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(RoomMember).options(selectinload(RoomMember.room).selectinload(Room.owner)).filter(
        RoomMember.user_id == current_user.id,
        RoomMember.status == RoomMemberStatus.INVITED
    )
    result = await db.execute(stmt)
    invites = result.scalars().all()
    
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
async def invite_user(
    room_id: str, 
    invite: InviteCreate, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    try:
        room_uid = uuid.UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Room ID format")

    result = await db.execute(select(Room).filter(Room.id == room_uid))
    room = result.scalars().first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    if room.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the room OWNER can invite members")
    
    res_user = await db.execute(select(User).filter(User.username == invite.username))
    target_user = res_user.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User to invite not found")
        
    # Check if already member/invited
    res_member = await db.execute(select(RoomMember).filter(RoomMember.room_id == room_uid, RoomMember.user_id == target_user.id))
    existing = res_member.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="User already invited or joined")
        
    new_member = RoomMember(
        room_id=room_uid,
        user_id=target_user.id,
        status=RoomMemberStatus.INVITED,
        permissions=invite.permissions
    )
    db.add(new_member)
    await db.commit()
    
    return {"message": f"Invitation sent to {invite.username}"}

@router.post("/{room_id}/join")
async def join_room(room_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        room_uid = uuid.UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Room ID format")

    res_member = await db.execute(select(RoomMember).filter(
        RoomMember.room_id == room_uid, 
        RoomMember.user_id == current_user.id,
        RoomMember.status == RoomMemberStatus.INVITED
    ))
    member = res_member.scalars().first()
    
    if not member:
        # Check if they are owner? Owner doesn't need to join.
        res_room = await db.execute(select(Room).filter(Room.id == room_uid))
        room = res_room.scalars().first()
        if room and room.owner_id == current_user.id:
             return {"message": "You are the owner of this room"}
        raise HTTPException(status_code=400, detail="No pending invitation found for this room")
        
    member.status = RoomMemberStatus.JOINED
    await db.commit()
    
    return {"message": "You have joined the room"}

@router.put("/{room_id}/status")
async def update_room_status(
    room_id: str, 
    is_online: bool, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    try:
        room_uid = uuid.UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Room ID format")

    res_room = await db.execute(select(Room).filter(Room.id == room_uid))
    room = res_room.scalars().first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    if room.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the room OWNER can change status")
        
    room.is_online = is_online
    await db.commit()
    
    return {"status": "updated", "is_online": is_online}

@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: str, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    try:
        room_uid = uuid.UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Room ID format")

    res_room = await db.execute(select(Room).filter(Room.id == room_uid))
    room = res_room.scalars().first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    if room.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the room OWNER can delete it")

    # Cascade delete members (if not handled by DB FK)
    members = await db.execute(select(RoomMember).filter(RoomMember.room_id == room_uid))
    for mem in members.scalars().all():
        await db.delete(mem)
    await db.delete(room)
    await db.commit()
    return None
