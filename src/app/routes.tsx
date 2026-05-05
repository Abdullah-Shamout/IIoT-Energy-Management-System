import { createBrowserRouter } from 'react-router';
import { Layout } from './Layout';
import { Dashboard } from './pages/Dashboard';
import { Chatbot } from './pages/Chatbot';

export const router = createBrowserRouter([
  {
    path: '/',
    Component: Layout,
    children: [
      { index: true, Component: Dashboard },
      { path: 'chatbot', Component: Chatbot },
    ],
  },
]);
