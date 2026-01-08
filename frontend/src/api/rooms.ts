import api from './client';
import { type Room, type Invitation } from '../types';

export interface CreateRoomData {
  name: string;
  description?: string;
  is_online?: boolean;
}

export const getRooms = async (): Promise<Room[]> => {
  const response = await api.get('/rooms/');
  return response.data;
};

export const createRoom = async (data: CreateRoomData): Promise<Room> => {
  const response = await api.post('/rooms/', data);
  return response.data;
};

export const getInvitations = async (): Promise<Invitation[]> => {
  const response = await api.get('/rooms/invitations');
  return response.data;
};

export const joinRoom = async (roomId: string): Promise<any> => {
  const response = await api.post(`/rooms/${roomId}/join`);
  return response.data;
};

export const inviteUser = async (roomId: string, username: string): Promise<any> => {
  const response = await api.post(`/rooms/${roomId}/invite`, { username });
  return response.data;
};
