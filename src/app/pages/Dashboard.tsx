import React, { useEffect, useState } from 'react';
import { getDashboardData } from '../services/api';
import { DashboardData } from '../types';
import { PieChartComponent } from '../components/PieChart';
import { DeviceStatus } from '../components/DeviceStatus';
import { LineGraph } from '../components/LineGraph';

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const dashboardData = await getDashboardData();
      setData(dashboardData);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    const interval = setInterval(fetchData, 15000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-200px)] bg-gray-50 dark:bg-gray-900">
        <span className="text-gray-600 dark:text-gray-400 text-base sm:text-lg">Loading dashboard...</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-200px)] bg-gray-50 dark:bg-gray-900">
        <span className="text-red-600 dark:text-red-400 text-base sm:text-lg">Failed to load dashboard data</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-3 sm:p-4 md:p-6">
      <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          <PieChartComponent data={data} />
          <DeviceStatus data={data} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          <LineGraph 
            title="Overall Energy Consumption" 
            color="#8B5CF6"
            deviceName="Consumption (kWh)"
          />
          <LineGraph 
            title="Fan Energy Consumption" 
            deviceId={1}
            color="#10B981"
            deviceName="Fan (kWh)"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          <LineGraph 
            title="Light Bulb Energy Consumption" 
            deviceId={3}
            color="#F59E0B"
            deviceName="Light Bulb (kWh)"
          />
          <LineGraph 
            title="Motor Energy Consumption" 
            deviceId={2}
            color="#3B82F6"
            deviceName="Motor (kWh)"
          />
        </div>
      </div>
    </div>
  );
};