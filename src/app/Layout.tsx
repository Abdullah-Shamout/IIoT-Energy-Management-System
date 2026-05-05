import React, { useEffect, useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router';
import { RefreshCw } from 'lucide-react';
import { Header } from './components/Header';
import { Navigation } from './components/Navigation';
import { getDashboardData } from './services/api';
import { DashboardData } from './types';

export const Layout: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  const fetchData = async () => {
    try {
      const dashboardData = await getDashboardData();
      setData(dashboardData);
    } catch (error) {
      console.error('Failed to fetch dashboard data for header:', error);
    }
  };

  useEffect(() => {
    fetchData();

    const interval = setInterval(fetchData, 15000);

    return () => clearInterval(interval);
  }, []);

  const handleToggle = () => {
    if (location.pathname === '/') {
      navigate('/chatbot');
    } else {
      navigate('/');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header data={data} />
      <Navigation />
      <div className="relative">
        <button
          onClick={handleToggle}
          className="absolute top-4 left-4 z-10 flex items-center justify-center w-10 h-10 bg-gray-900 dark:bg-gray-800 hover:bg-gray-700 dark:hover:bg-gray-600 text-white rounded-full shadow-lg transition-all hover:scale-110"
          aria-label="Switch page"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
        <Outlet />
      </div>
    </div>
  );
};