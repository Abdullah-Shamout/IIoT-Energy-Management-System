export interface Device {
  id: number;
  device_name: string;
  device_intensity: string | null;
  device_status: string;
  device_total_consumption: number;
}

export interface SensorReading {
  id: number;
  iot_device_id: number;
  reading_time: string;
  voltage: number;
  current: number;
  power: number;
}

export interface SystemConfig {
  id: number;
  data_collection_frequency: number;
  energy_budget: number;
  comparison_period: string;
  total_consumption: number;
}

export interface DashboardData {
  devices: Device[];
  systemConfig: SystemConfig;
  remainingBudget: number;
  consumptionStatus: string;
  efficiencyScore: number;
  consumptionPercentage: number;
}

export interface ChartDataPoint {
  time: string;
  value: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

// Represents a single pending action in the backend scheduler
export interface ScheduledAction {
  id: string;
  device: string;
  action: string;
  value: string | number | null;
  scheduled_time: string; // ISO8601 Kuwait time string, e.g. "2025-04-21T16:00:00+03:00"
  status: "pending" | "executed" | "cancelled";
}
