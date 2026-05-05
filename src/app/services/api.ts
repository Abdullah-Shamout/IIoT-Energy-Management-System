import axios from "axios";
import { DashboardData, ChartDataPoint, ChatMessage } from "../types";

const API_BASE_URL = "http://raspberrypi-ip-address:5000/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000,
});

export const getDashboardData = async (): Promise<DashboardData> => {
  const response = await api.get("/dashboard");
  return response.data;
};

export const updateEnergyBudget = async (budget: number): Promise<void> => {
  await api.post("/energy-budget", { budget });
};

export const getChartData = async (
  deviceId?: number,
): Promise<ChartDataPoint[]> => {
  const endpoint = deviceId
    ? `/chart-data?device_id=${deviceId}`
    : "/chart-data";
  const response = await api.get(endpoint);
  return response.data;
};

export const sendChatMessage = async (message: string): Promise<string> => {
  const response = await api.post("/chat", { message });
  return response.data.response;
};

export const getChatHistory = async (): Promise<ChatMessage[]> => {
  const response = await api.get("/chat/history");
  return response.data;
};

export default api;
