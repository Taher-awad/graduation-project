export enum UserRole {
  STAFF = "STAFF",
  STUDENT = "STUDENT"
}

export enum AssetType {
  MODEL = "MODEL",
  VIDEO = "VIDEO",
  SLIDE = "SLIDE"
}

export enum AssetStatus {
  PENDING = "PENDING",
  PROCESSING = "PROCESSING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED"
}

export interface User {
  username: string;
  role: UserRole;
}

export interface Asset {
  id: string;
  filename: string;
  asset_type: AssetType;
  status: AssetStatus;
  is_sliceable: boolean;
  download_url?: string;
  metadata?: any;
}

export interface Room {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  is_online: boolean;
  active_users_count: number;
  role_in_room: "OWNER" | "MEMBER";
  created_at: string;
}

export interface Invitation {
  room_id: string;
  room_name: string;
  invited_by: string;
  status: "INVITED" | "JOINED";
}
