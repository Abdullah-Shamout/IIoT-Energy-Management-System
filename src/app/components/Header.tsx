import React, { useState } from 'react';
import { Moon, Sun, Zap, TrendingDown, DollarSign, Activity, AlertCircle, Menu } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { DashboardData } from '../types';
import { EnergyBudgetModal } from './EnergyBudgetModal';

interface HeaderProps {
  data: DashboardData | null;
}

export const Header: React.FC<HeaderProps> = ({ data }) => {
  const { theme, toggleTheme } = useTheme();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);

  if (!data) return null;

  const { systemConfig, remainingBudget, consumptionStatus, efficiencyScore, consumptionPercentage } = data;

  return (
    <>
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-4 sm:px-6 py-3 sm:py-4">
        {/* Desktop Header */}
        <div className="hidden lg:flex items-center justify-between">
          <h1 className="text-xl xl:text-2xl font-semibold text-gray-900 dark:text-white whitespace-nowrap">
            Energy Management System
          </h1>

          <div className="flex items-center gap-3 xl:gap-6 flex-wrap">
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 px-2 xl:px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <Zap className="w-4 h-4 text-blue-500 flex-shrink-0" />
              <div className="text-left">
                <div className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">Energy Budget</div>
                <div className="text-sm font-semibold text-gray-900 dark:text-white whitespace-nowrap">
                  {systemConfig.energy_budget.toLocaleString()} kWh
                </div>
              </div>
            </button>

            <div className="flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-orange-500 flex-shrink-0" />
              <div className="text-left">
                <div className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">Current Consumption</div>
                <div className="text-sm font-semibold text-gray-900 dark:text-white whitespace-nowrap">
                  {(systemConfig.total_consumption / 1000).toFixed(2)} kWh
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-green-500 flex-shrink-0" />
              <div className="text-left">
                <div className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">Remaining Budget</div>
                <div className="text-sm font-semibold text-gray-900 dark:text-white whitespace-nowrap">
                  {(remainingBudget / 1000).toFixed(2)} kWh
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-500 flex-shrink-0" />
              <div className="text-left">
                <div className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">Efficiency Score</div>
                <div className="text-sm font-semibold text-gray-900 dark:text-white whitespace-nowrap">
                  {efficiencyScore.toFixed(1)}%
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-gray-500 flex-shrink-0" />
              <div className="text-left">
                <div className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">System Status</div>
                <div className="text-sm font-semibold">
                  <span className={consumptionStatus === 'Normal' ? 'text-green-500' : 'text-red-500'}>
                    {consumptionStatus}
                  </span>
                </div>
              </div>
            </div>

            <div className={`px-3 py-1 rounded-full text-sm font-semibold whitespace-nowrap ${
              consumptionPercentage < 80 ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
              consumptionPercentage < 100 ? 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300' :
              'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
            }`}>
              {consumptionPercentage.toFixed(1)}%
            </div>

            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex-shrink-0"
              aria-label="Toggle theme"
            >
              {theme === 'light' ? (
                <Moon className="w-5 h-5 text-gray-700 dark:text-gray-300" />
              ) : (
                <Sun className="w-5 h-5 text-gray-700 dark:text-gray-300" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile/Tablet Header */}
        <div className="lg:hidden">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-white">
              Energy Management
            </h1>
            <div className="flex items-center gap-2">
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                aria-label="Toggle theme"
              >
                {theme === 'light' ? (
                  <Moon className="w-5 h-5 text-gray-700 dark:text-gray-300" />
                ) : (
                  <Sun className="w-5 h-5 text-gray-700 dark:text-gray-300" />
                )}
              </button>
              <button
                onClick={() => setShowMobileMenu(!showMobileMenu)}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                aria-label="Toggle menu"
              >
                <Menu className="w-5 h-5 text-gray-700 dark:text-gray-300" />
              </button>
            </div>
          </div>

          {/* Mobile Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3">
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <Zap className="w-4 h-4 text-blue-500 flex-shrink-0" />
              <div className="text-left min-w-0">
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">Budget</div>
                <div className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                  {systemConfig.energy_budget.toLocaleString()} kWh
                </div>
              </div>
            </button>

            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800">
              <TrendingDown className="w-4 h-4 text-orange-500 flex-shrink-0" />
              <div className="text-left min-w-0">
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">Current</div>
                <div className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                  {(systemConfig.total_consumption / 1000).toFixed(2)} kWh
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800">
              <DollarSign className="w-4 h-4 text-green-500 flex-shrink-0" />
              <div className="text-left min-w-0">
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">Remaining</div>
                <div className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                  {(remainingBudget / 1000).toFixed(2)} kWh
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800">
              <Activity className="w-4 h-4 text-purple-500 flex-shrink-0" />
              <div className="text-left min-w-0">
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">Efficiency</div>
                <div className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                  {efficiencyScore.toFixed(1)}%
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800">
              <AlertCircle className="w-4 h-4 text-gray-500 flex-shrink-0" />
              <div className="text-left min-w-0">
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">Status</div>
                <div className="text-sm font-semibold">
                  <span className={consumptionStatus === 'Normal' ? 'text-green-500' : 'text-red-500'}>
                    {consumptionStatus}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-center px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800">
              <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
                consumptionPercentage < 80 ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                consumptionPercentage < 100 ? 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300' :
                'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
              }`}>
                {consumptionPercentage.toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </header>

      <EnergyBudgetModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)}
        currentBudget={systemConfig.energy_budget}
      />
    </>
  );
};