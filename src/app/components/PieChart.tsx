import React from 'react';
import { PieChart as RechartsPieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { DashboardData } from '../types';

interface PieChartProps {
  data: DashboardData;
}

export const PieChartComponent: React.FC<PieChartProps> = ({ data }) => {
  const { devices, remainingBudget } = data;

  const motorDevice = devices.find(d => d.id === 2);
  const fanDevice = devices.find(d => d.id === 1);
  const lightDevice = devices.find(d => d.id === 3);

  const motorConsumption = motorDevice?.device_total_consumption || 0;
  const fanConsumption = fanDevice?.device_total_consumption || 0;
  const lightConsumption = lightDevice?.device_total_consumption || 0;

  const total = motorConsumption + fanConsumption + lightConsumption + remainingBudget;

  const chartData = [
    {
      name: 'Motor',
      value: motorConsumption,
      percentage: total > 0 ? ((motorConsumption / total) * 100).toFixed(1) : '0.0',
      color: '#3B82F6',
    },
    {
      name: 'Light Bulb',
      value: lightConsumption,
      percentage: total > 0 ? ((lightConsumption / total) * 100).toFixed(1) : '0.0',
      color: '#F59E0B',
    },
    {
      name: 'Fan',
      value: fanConsumption,
      percentage: total > 0 ? ((fanConsumption / total) * 100).toFixed(1) : '0.0',
      color: '#10B981',
    },
    {
      name: 'Remaining Budget',
      value: remainingBudget > 0 ? remainingBudget : 0,
      percentage: total > 0 ? ((Math.max(remainingBudget, 0) / total) * 100).toFixed(1) : '0.0',
      color: '#9CA3AF',
    },
  ];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 shadow-sm border border-gray-200 dark:border-gray-700">
      <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-4">Consumption by Device</h3>
      <ResponsiveContainer width="100%" height={250} className="sm:h-[300px]">
        <RechartsPieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percentage }) => `${name} ${percentage}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number) => `${(value / 1000).toFixed(2)} kWh`} />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
        </RechartsPieChart>
      </ResponsiveContainer>
    </div>
  );
};