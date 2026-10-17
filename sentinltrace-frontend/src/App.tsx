import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/layouts/AppShell";
import { UserShell } from "@/layouts/UserShell";
import { WorkspaceProvider } from "@/hooks/useWorkspace";
import { AuthProvider } from "@/hooks/useAuth";
import { RequireAnalystAuth, RequireUserAuth } from "@/components/auth/RouteGuards";

// Public
import { LandingPage } from "@/pages/public/LandingPage";
import { AnalystLogin } from "@/pages/public/AnalystLogin";
import { UserLogin } from "@/pages/public/UserLogin";

// Existing analyst application (protected, unchanged internally)
import { Dashboard } from "@/pages/Dashboard";
import { Complaints } from "@/pages/Complaints";
import { ComplaintDetail } from "@/pages/ComplaintDetail";
import { Accounts } from "@/pages/Accounts";
import { AccountDetail } from "@/pages/AccountDetail";
import { Networks } from "@/pages/Networks";
import { CashOutIntelligence } from "@/pages/CashOutIntelligence";
import { Predictions } from "@/pages/Predictions";
import { ModelEvaluation } from "@/pages/ModelEvaluation";
import { InvestigationWorkspace } from "@/pages/InvestigationWorkspace";
import { SystemStatus } from "@/pages/SystemStatus";
import { SettingsPage } from "@/pages/SettingsPage";

// User portal (new)
import { UserDashboard } from "@/pages/user/UserDashboard";
import { ReportComplaint } from "@/pages/user/ReportComplaint";
import { MyComplaints } from "@/pages/user/MyComplaints";
import { TrackComplaint } from "@/pages/user/TrackComplaint";
import { Notifications } from "@/pages/user/Notifications";
import { UserProfile } from "@/pages/user/UserProfile";

export default function App() {
  return (
    <AuthProvider>
      <WorkspaceProvider>
        <BrowserRouter>
          <Routes>
            {/* Public */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/analyst/login" element={<AnalystLogin />} />
            <Route path="/user/login" element={<UserLogin />} />

            {/* Existing analyst application — moved under /analyst, otherwise untouched */}
            <Route
              path="/analyst"
              element={
                <RequireAnalystAuth>
                  <AppShell />
                </RequireAnalystAuth>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="complaints" element={<Complaints />} />
              <Route path="complaints/:id" element={<ComplaintDetail />} />
              <Route path="accounts" element={<Accounts />} />
              <Route path="accounts/:id" element={<AccountDetail />} />
              <Route path="networks" element={<Networks />} />
              <Route path="cashout" element={<CashOutIntelligence />} />
              <Route path="predictions" element={<Predictions />} />
              <Route path="analytics" element={<ModelEvaluation />} />
              <Route path="workspace" element={<InvestigationWorkspace />} />
              <Route path="system" element={<SystemStatus />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            {/* New user portal */}
            <Route
              path="/user"
              element={
                <RequireUserAuth>
                  <UserShell />
                </RequireUserAuth>
              }
            >
              <Route index element={<UserDashboard />} />
              <Route path="report" element={<ReportComplaint />} />
              <Route path="complaints" element={<MyComplaints />} />
              <Route path="track" element={<TrackComplaint />} />
              <Route path="notifications" element={<Notifications />} />
              <Route path="profile" element={<UserProfile />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </WorkspaceProvider>
    </AuthProvider>
  );
}
