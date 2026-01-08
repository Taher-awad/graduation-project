import { useState, useEffect } from 'react';
import { 
  Users, 
  Plus, 
  MessageSquare 
} from 'lucide-react';
import { getRooms, createRoom, getInvitations, joinRoom } from '../api/rooms';
import type { Room, Invitation } from '../types';

export const Rooms = () => {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newRoomName, setNewRoomName] = useState('');
  const [loading, setLoading] = useState(true);

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const isStaff = user.role === 'STAFF';

  const fetchData = async () => {
    try {
      setLoading(true);
      const [roomsData, invitesData] = await Promise.all([
        getRooms(),
        getInvitations()
      ]);
      setRooms(roomsData);
      setInvitations(invitesData);
    } catch (err: any) {
      console.error(err);
      // alert('Failed to load rooms'); 
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createRoom({ name: newRoomName });
      setIsCreateModalOpen(false);
      setNewRoomName('');
      fetchData();
    } catch (err: any) {
      alert('Failed to create room');
    }
  };

  const handleJoinRoom = async (roomId: string) => {
    try {
      await joinRoom(roomId);
      fetchData(); // Refresh to see the room in list
      alert('Joined room successfully');
    } catch (err) {
      alert('Failed to join room');
    }
  };

  if (loading) return <div className="text-white p-8">Loading rooms...</div>;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400">
            Collaboration Rooms
          </h1>
          <p className="text-slate-400 mt-2">Join a session or create your own</p>
        </div>
        
        {isStaff && (
          <button 
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg transition-colors shadow-lg shadow-blue-500/20"
          >
            <Plus size={20} />
            Create Room
          </button>
        )}
      </div>

      {/* Invitations Section */}
      {invitations.length > 0 && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <MessageSquare size={20} className="text-yellow-400" />
            Pending Invitations
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {invitations.map((invite) => (
              <div key={invite.room_id} className="bg-slate-900 border border-slate-700 p-4 rounded-lg flex items-center justify-between">
                <div>
                  <div className="font-medium text-white">{invite.room_name}</div>
                  <div className="text-sm text-slate-400">Invited by {invite.invited_by}</div>
                </div>
                <button
                  onClick={() => handleJoinRoom(invite.room_id)}
                  className="px-3 py-1 bg-green-600 hover:bg-green-500 text-white text-sm rounded transition-colors"
                >
                  Join
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rooms List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {rooms.map((room) => (
          <div key={room.id} className="group bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-slate-600 rounded-xl p-6 transition-all duration-300">
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-indigo-500/10 rounded-lg group-hover:bg-indigo-500/20 transition-colors">
                <Users className="text-indigo-400" size={24} />
              </div>
              <div className={`px-2 py-1 rounded text-xs font-medium ${
                room.is_online ? 'bg-green-500/10 text-green-400' : 'bg-slate-700 text-slate-400'
              }`}>
                {room.is_online ? 'ONLINE' : 'OFFLINE'}
              </div>
            </div>
            
            <h3 className="text-xl font-bold text-white mb-2">{room.name}</h3>
            <p className="text-slate-400 text-sm mb-4 line-clamp-2">
              {room.description || 'No description provided'}
            </p>
            
            <div className="flex items-center justify-between mt-auto pt-4 border-t border-slate-700/50">
              <span className="text-slate-500 text-sm">
                0 participants
              </span>
              <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors text-sm font-medium">
                Enter Room
              </button>
            </div>
          </div>
        ))}

        {rooms.length === 0 && (
            <div className="col-span-full text-center py-12 text-slate-500">
                No rooms found. {isStaff ? 'Create one to get started!' : 'Wait for an invitation.'}
            </div>
        )}
      </div>

        {/* Create Room Modal */}
        {isCreateModalOpen && (
            <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
                <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-md p-6">
                    <h2 className="text-xl font-bold text-white mb-4">Create New Room</h2>
                    <form onSubmit={handleCreateRoom} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1">Room Name</label>
                            <input 
                                type="text"
                                value={newRoomName}
                                onChange={e => setNewRoomName(e.target.value)}
                                className="w-full bg-slate-800 border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-blue-500 outline-none"
                                required
                            />
                        </div>
                        <div className="flex gap-3 justify-end mt-6">
                            <button 
                                type="button"
                                onClick={() => setIsCreateModalOpen(false)}
                                className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button 
                                type="submit"
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                            >
                                Create
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        )}
    </div>
  );
};
