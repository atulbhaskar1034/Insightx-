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
    <Sidebar className="border-r border-white/[0.06]">
      <SidebarContent className="flex flex-col h-full">
        {/* ── Brand Header ─────────────────────────────────────────────── */}
        <div className="px-4 pt-5 pb-2">
          <Link
            to="/"
            className="flex items-center gap-2.5 group"
          >
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-black text-white"
              style={{
                background: "linear-gradient(135deg, #8b5cf6, #06b6d4)",
                boxShadow: "0 0 20px -4px rgba(139, 92, 246, 0.4)",
              }}
            >
              IX
            </div>
            <span className="text-sm font-semibold text-slate-200 group-hover:text-white transition-colors">
              InsightX
            </span>
          </Link>
        </div>

        {/* ── New Chat Button ──────────────────────────────────────────── */}
        <div className="px-3 pt-2 pb-1">
          <button
            onClick={onNewChat}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium 
                       border border-white/[0.08] bg-white/[0.04]
                       text-slate-300 hover:text-white hover:bg-white/[0.08] hover:border-white/[0.12]
                       transition-all duration-200 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>
        </div>

        {/* ── Session List ─────────────────────────────────────────────── */}
        <SidebarGroup className="flex-1 overflow-y-auto pt-1">
          <SidebarGroupLabel className="px-4 text-[10px] font-semibold text-slate-500 uppercase tracking-[0.1em]">
            Recent
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="px-2 space-y-0.5">
              {sessions.length === 0 && (
                <div className="px-3 py-6 text-center">
                  <Sparkles className="w-5 h-5 text-slate-600 mx-auto mb-2" />
                  <p className="text-xs text-slate-600">
                    No conversations yet
                  </p>
                  <p className="text-[10px] text-slate-700 mt-0.5">
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
                          ? "bg-white/[0.08] text-white"
                          : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
                        }`
                      }
                      onClick={() => navigate(`/dashboard/${session.id}`)}
                    >
                      {/* Active indicator bar */}
                      {isActive && (
                        <div
                          className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full"
                          style={{
                            background: "linear-gradient(180deg, #8b5cf6, #06b6d4)",
                          }}
                        />
                      )}
                      <MessageSquare
                        className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-violet-400" : "text-slate-600"
                          }`}
                      />
                      <span className="flex-1 text-[13px] truncate leading-tight">
                        {session.title}
                      </span>
                      {/* Time — visible normally, hidden on hover to show delete */}
                      <span className="text-[10px] text-slate-600 shrink-0 group-hover:hidden">
                        {timeAgo(session.updated_at)}
                      </span>
                      {/* Delete — hidden normally, visible on hover */}
                      <button
                        onClick={(e) => handleDelete(e, session.id)}
                        className="hidden group-hover:flex items-center justify-center w-5 h-5 rounded-md 
                                   text-slate-500 hover:text-red-400 hover:bg-red-400/10
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
        <div className="mt-auto border-t border-white/[0.06] px-3 py-3 space-y-0.5">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton asChild>
                <Link
                  to="/"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] transition-all"
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
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] transition-all"
                >
                  <TrendingUp className="w-4 h-4" />
                  <span className="text-[13px]">Predictions</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] transition-all cursor-pointer">
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
