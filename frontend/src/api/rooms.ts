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

export const joinRoom = async (roomId: string): Promise<unknown> => {
  const response = await api.post(`/rooms/${roomId}/join`);
  return response.data;
};

export const inviteUser = async (roomId: string, username: string): Promise<unknown> => {
  const response = await api.post(`/rooms/${roomId}/invite`, { username });
  return response.data;
};

export const deleteRoom = async (roomId: string): Promise<void> => {
  await api.delete(`/rooms/${roomId}`);
};

export const updateRoomStatus = async (roomId: string, is_online: boolean): Promise<unknown> => {
  const response = await api.put(`/rooms/${roomId}/status?is_online=${is_online}`);
  return response.data;
};
