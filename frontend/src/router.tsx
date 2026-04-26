import { createBrowserRouter } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { DashboardPage } from '@/pages/DashboardPage';
import { RecordsPage } from '@/pages/RecordsPage';
import { ImportPage } from '@/pages/ImportPage';
import { CategoriesPage } from '@/pages/CategoriesPage';
import { SettingsPage } from '@/pages/SettingsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage />, handle: { title: 'Home' } },
      { path: 'records', element: <RecordsPage />, handle: { title: 'Records' } },
      { path: 'import', element: <ImportPage />, handle: { title: 'Import' } },
      { path: 'categories', element: <CategoriesPage />, handle: { title: 'Categories' } },
      { path: 'settings', element: <SettingsPage />, handle: { title: 'Settings' } },
    ],
  },
]);
