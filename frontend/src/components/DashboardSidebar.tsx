import { useEffect, useState, useCallback } from "react";
import {
  Plus,
  MessageSquare,
  Settings,
  Home,
  Trash2,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { listSessions, deleteSession, type ChatSession } from "@/lib/api";

// -- Relative time helper -----------------------------------------------------

function timeAgo(isoStr: string): string {
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "1d";
  if (days < 7) return `${days}d`;
  return `${Math.floor(days / 7)}w`;
}

// -- Props --------------------------------------------------------------------

interface DashboardSidebarProps {
  activeSessionId?: string | null;
  onNewChat: () => void;
  refreshKey?: number;
}

// -- Component ----------------------------------------------------------------

const DashboardSidebar = ({
  activeSessionId,
  onNewChat,
  refreshKey,
}: DashboardSidebarProps) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const navigate = useNavigate();

  const loadSessions = useCallback(async () => {
    try {
      const data = await listSessions();
      setSessions(data);
    } catch {
      // silently ignore
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions, refreshKey]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    e.preventDefault();
    try {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) onNewChat();
    } catch {
      // ignore
    }
  };

  return (
    <Sidebar className="border-r border-gray-200">
      <SidebarContent className="flex flex-col h-full bg-white">
        {/* ── Brand Header ─────────────────────────────────────────────── */}
        <div className="px-4 pt-5 pb-2">
          <Link
            to="/"
            className="flex items-center gap-2.5 group"
          >
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-black text-white"
              style={{
                background: "linear-gradient(135deg, #f97316, #ec4899)",
                boxShadow: "0 0 15px -4px rgba(249, 115, 22, 0.3)",
              }}
            >
              IX
            </div>
            <span className="text-sm font-semibold text-gray-700 group-hover:text-gray-900 transition-colors">
              InsightX
            </span>
          </Link>
        </div>

        {/* ── New Chat Button ──────────────────────────────────────────── */}
        <div className="px-3 pt-2 pb-1">
          <button
            onClick={onNewChat}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium 
                       border border-gray-200 bg-gray-50
                       text-gray-600 hover:text-gray-900 hover:bg-gray-100 hover:border-gray-300
                       transition-all duration-200 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>
        </div>

        {/* ── Session List ─────────────────────────────────────────────── */}
        <SidebarGroup className="flex-1 overflow-y-auto pt-1">
          <SidebarGroupLabel className="px-4 text-[10px] font-semibold text-gray-400 uppercase tracking-[0.1em]">
            Recent
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="px-2 space-y-0.5">
              {sessions.length === 0 && (
                <div className="px-3 py-6 text-center">
                  <Sparkles className="w-5 h-5 text-gray-300 mx-auto mb-2" />
                  <p className="text-xs text-gray-400">
                    No conversations yet
                  </p>
                  <p className="text-[10px] text-gray-300 mt-0.5">
                    Start by asking a question
                  </p>
                </div>
              )}
              {sessions.map((session) => {
                const isActive = session.id === activeSessionId;
                return (
                  <SidebarMenuItem key={session.id}>
                    <SidebarMenuButton
                      className={`group relative flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer transition-all duration-150
                        ${isActive
                          ? "bg-orange-50 text-gray-900 border border-orange-200"
                          : "text-gray-500 hover:text-gray-800 hover:bg-gray-50"
                        }`
                      }
                      onClick={() => navigate(`/dashboard/${session.id}`)}
                    >
                      {/* Active indicator bar */}
                      {isActive && (
                        <div
                          className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full"
                          style={{
                            background: "linear-gradient(180deg, #f97316, #ec4899)",
                          }}
                        />
                      )}
                      <MessageSquare
                        className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-orange-500" : "text-gray-400"
                          }`}
                      />
                      <span className="flex-1 text-[13px] truncate leading-tight">
                        {session.title}
                      </span>
                      {/* Time — visible normally, hidden on hover to show delete */}
                      <span className="text-[10px] text-gray-400 shrink-0 group-hover:hidden">
                        {timeAgo(session.updated_at)}
                      </span>
                      {/* Delete — hidden normally, visible on hover */}
                      <button
                        onClick={(e) => handleDelete(e, session.id)}
                        className="hidden group-hover:flex items-center justify-center w-5 h-5 rounded-md 
                                   text-gray-400 hover:text-red-500 hover:bg-red-50
                                   transition-colors shrink-0"
                        title="Delete chat"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* ── Bottom Nav ───────────────────────────────────────────────── */}
        <div className="mt-auto border-t border-gray-200 px-3 py-3 space-y-0.5">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton asChild>
                <Link
                  to="/"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-50 transition-all"
                >
                  <Home className="w-4 h-4" />
                  <span className="text-[13px]">Home</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton asChild>
                <Link
                  to="/predictions"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-50 transition-all"
                >
                  <TrendingUp className="w-4 h-4" />
                  <span className="text-[13px]">Predictions</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-50 transition-all cursor-pointer">
                <Settings className="w-4 h-4" />
                <span className="text-[13px]">Settings</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </div>
      </SidebarContent>
    </Sidebar>
  );
};

export default DashboardSidebar;
