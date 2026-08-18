import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from './components/AppShell'
import { LogsPage, ProfilePage, SourcesPage, TodosPage } from './components/UtilityPages'
import { ContentDetailPage } from './features/content/ContentDetailPage'
import { ContentPage } from './features/content/ContentPage'
import { DashboardPage } from './features/dashboard/DashboardPage'
import { MapOverviewPage } from './features/map/MapOverviewPage'
import { PlaceDetailPage } from './features/map/PlaceDetailPage'
import { RoutesPage } from './features/map/RoutesPage'
import { SettingsPage } from './features/settings/SettingsPage'
import { CapturePage } from './features/tasks/CapturePage'
import { TaskDetailPage } from './features/tasks/TaskDetailPage'
import { TasksPage } from './features/tasks/TasksPage'

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/content" element={<ContentPage />} />
        <Route path="/content/:contentId" element={<ContentDetailPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/tasks/:jobId" element={<TaskDetailPage />} />
        <Route path="/sources" element={<SourcesPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/logs" element={<LogsPage />} />
        <Route path="/capture" element={<CapturePage />} />
        <Route path="/todos" element={<TodosPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/map" element={<MapOverviewPage />} />
        <Route path="/places/:placeId" element={<PlaceDetailPage />} />
        <Route path="/routes" element={<RoutesPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  )
}
