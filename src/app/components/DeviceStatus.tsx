import React from 'react';
import { DashboardData } from '../types';

interface DeviceStatusProps {
  data: DashboardData;
}

export const DeviceStatus: React.FC<DeviceStatusProps> = ({ data }) => {
  const { devices } = data;

  const getStatusColor = (status: string) => {
    return status.toLowerCase() === 'on' 
      ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
      : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
  };

  const getDeviceColor = (id: number) => {
    switch (id) {
      case 2: return 'bg-blue-500';
      case 3: return 'bg-orange-500';
      case 1: return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-4">Device Status</h3>
      <div className="space-y-3">
        {devices.map((device) => (
          <div key={device.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50">
            <div className="flex items-center gap-3 min-w-0">
              <div className={`w-3 h-3 rounded-full flex-shrink-0 ${getDeviceColor(device.id)}`} />
              <span className="text-sm sm:text-base text-gray-900 dark:text-white font-medium truncate">{device.device_name}</span>
            </div>
            <span className={`px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm font-semibold whitespace-nowrap ${getStatusColor(device.device_status)}`}>
              {device.device_status.toUpperCase()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};