export const UserRole = {
  TEACHER: "TEACHER",
  TA: "TA",
  STUDENT: "STUDENT",
} as const;

export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export const AssetType = {
  MODEL: "MODEL",
  VIDEO: "VIDEO",
  SLIDE: "SLIDE",
  IMAGE: "IMAGE"
} as const;

export type AssetType = (typeof AssetType)[keyof typeof AssetType];

export const AssetStatus = {
  PENDING: "PENDING",
  SCANNING: "SCANNING",
  PENDING_SELECTION: "PENDING_SELECTION",
  PROCESSING: "PROCESSING",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED"
} as const;

export type AssetStatus = (typeof AssetStatus)[keyof typeof AssetStatus];

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
  metadata_json?: Record<string, unknown>;
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
