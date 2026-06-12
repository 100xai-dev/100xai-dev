"use client";

import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from "react";
import type { ReactNode } from "react";

import { dstr, PF, SEED_POSTS, TODAY, type PlatformKey, type Post } from "./data";
import { DEFAULT_BRAND, type BrandData } from "./persona";

type ViewMode = "week" | "month" | "list";
type Filters = Record<PlatformKey, boolean>;

interface ComposeState {
  open: boolean;
  editingId: number | null;
  title: string;
  text: string;
  date: string;
  time: string;
  channels: PlatformKey[];
}

interface ToastState {
  show: boolean;
  msg: string;
  ai: boolean;
}

interface SchedulerCtx {
  brand: BrandData;
  setBrand: (b: BrandData) => void;

  posts: Post[];
  filters: Filters;
  toggleFilter: (pf: PlatformKey) => void;

  view: ViewMode;
  setView: (v: ViewMode) => void;
  viewAnchor: Date;
  shiftDate: (dir: number) => void;
  goToday: () => void;

  search: string;
  setSearch: (s: string) => void;
  visiblePosts: () => Post[];

  movePost: (id: number, date: string, time: string) => void;

  compose: ComposeState;
  openCompose: () => void;
  editPost: (id: number) => void;
  quickAdd: (date: string, time: string) => void;
  closeCompose: () => void;
  updateCompose: (patch: Partial<ComposeState>) => void;
  toggleComposeChannel: (pf: PlatformKey) => void;
  submitCompose: () => void;

  toast: ToastState;
  showToast: (msg: string, ai?: boolean) => void;
}

const Ctx = createContext<SchedulerCtx | null>(null);

const DEFAULT_COMPOSE_TEXT =
  "Driver Dignity is not charity — it's infrastructure. This week we enrolled 240 more truck drivers into the Rakshak welfare program across the Maharashtra corridor.";

const BRAND_KEY = "schedulr.brand";

export function SchedulerProvider({ children }: { children: ReactNode }) {
  const [brand, setBrandState] = useState<BrandData>(DEFAULT_BRAND);
  const [posts, setPosts] = useState<Post[]>(SEED_POSTS);
  const [filters, setFilters] = useState<Filters>({ blog: true, li: true, ig: true });
  const [view, setView] = useState<ViewMode>("week");
  const [viewAnchor, setViewAnchor] = useState<Date>(new Date(TODAY));
  const [search, setSearch] = useState("");
  const [nextId, setNextId] = useState(100);
  const [compose, setCompose] = useState<ComposeState>({
    open: false, editingId: null, title: "Create post",
    text: DEFAULT_COMPOSE_TEXT, date: dstr(TODAY), time: "10:00", channels: ["blog", "li"],
  });
  const [toast, setToast] = useState<ToastState>({ show: false, msg: "", ai: false });

  // hydrate brand from localStorage (set during onboarding)
  useEffect(() => {
    try {
      const raw = localStorage.getItem(BRAND_KEY);
      if (raw) setBrandState(JSON.parse(raw));
    } catch {
      /* ignore */
    }
  }, []);

  const setBrand = useCallback((b: BrandData) => {
    setBrandState(b);
    try {
      localStorage.setItem(BRAND_KEY, JSON.stringify(b));
    } catch {
      /* ignore */
    }
  }, []);

  const showToast = useCallback((msg: string, ai = false) => {
    setToast({ show: true, msg, ai });
  }, []);

  useEffect(() => {
    if (!toast.show) return;
    const t = setTimeout(() => setToast((s) => ({ ...s, show: false })), 3200);
    return () => clearTimeout(t);
  }, [toast.show, toast.msg]);

  const toggleFilter = useCallback((pf: PlatformKey) => {
    setFilters((f) => ({ ...f, [pf]: !f[pf] }));
  }, []);

  const shiftDate = useCallback((dir: number) => {
    setViewAnchor((prev) => {
      const d = new Date(prev);
      if (view === "month") d.setMonth(d.getMonth() + dir);
      else d.setDate(d.getDate() + dir * 7);
      return d;
    });
  }, [view]);

  const goToday = useCallback(() => setViewAnchor(new Date(TODAY)), []);

  const visiblePosts = useCallback(() => {
    const q = search.toLowerCase();
    return posts
      .filter((p) => filters[p.pf])
      .filter((p) => !q || p.text.toLowerCase().includes(q));
  }, [posts, filters, search]);

  const movePost = useCallback((id: number, date: string, time: string) => {
    setPosts((prev) => prev.map((p) => (p.id === id ? { ...p, date, time } : p)));
  }, []);

  const openCompose = useCallback(() => {
    setCompose({
      open: true, editingId: null, title: "Create post",
      text: DEFAULT_COMPOSE_TEXT, date: dstr(viewAnchor), time: "10:00", channels: ["blog", "li"],
    });
  }, [viewAnchor]);

  const editPost = useCallback((id: number) => {
    setPosts((prev) => {
      const p = prev.find((x) => x.id === id);
      if (p) {
        setCompose({
          open: true, editingId: id, title: "Edit post",
          text: p.text, date: p.date, time: p.time, channels: [p.pf],
        });
      }
      return prev;
    });
  }, []);

  const quickAdd = useCallback((date: string, time: string) => {
    setCompose({
      open: true, editingId: null, title: "Create post",
      text: "", date, time, channels: ["li"],
    });
  }, []);

  const closeCompose = useCallback(() => setCompose((c) => ({ ...c, open: false })), []);

  const updateCompose = useCallback((patch: Partial<ComposeState>) => {
    setCompose((c) => ({ ...c, ...patch }));
  }, []);

  const toggleComposeChannel = useCallback((pf: PlatformKey) => {
    setCompose((c) => ({
      ...c,
      channels: c.channels.includes(pf) ? c.channels.filter((x) => x !== pf) : [...c.channels, pf],
    }));
  }, []);

  const submitCompose = useCallback(() => {
    setCompose((c) => {
      const text = c.text.trim();
      if (!text) {
        showToast("Add some content first");
        return c;
      }
      if (!c.channels.length) {
        showToast("Pick at least one channel");
        return c;
      }
      if (c.editingId != null) {
        setPosts((prev) => prev.map((p) =>
          p.id === c.editingId
            ? { ...p, text, date: c.date, time: c.time, pf: c.channels[0], status: "scheduled" }
            : p,
        ));
        showToast("Post updated & scheduled");
      } else {
        setPosts((prev) => {
          const added: Post[] = c.channels.map((pf, i) => ({
            id: nextId + i, pf, date: c.date, time: c.time, status: "scheduled", text,
          }));
          return [...prev, ...added];
        });
        setNextId((n) => n + c.channels.length);
        showToast(c.channels.length > 1 ? `Scheduled across ${c.channels.length} channels` : "Post scheduled");
      }
      return { ...c, open: false };
    });
  }, [nextId, showToast]);

  const value = useMemo<SchedulerCtx>(() => ({
    brand, setBrand,
    posts, filters, toggleFilter,
    view, setView, viewAnchor, shiftDate, goToday,
    search, setSearch, visiblePosts,
    movePost,
    compose, openCompose, editPost, quickAdd, closeCompose, updateCompose, toggleComposeChannel, submitCompose,
    toast, showToast,
  }), [
    brand, setBrand, posts, filters, toggleFilter, view, viewAnchor, shiftDate, goToday,
    search, visiblePosts, movePost, compose, openCompose, editPost, quickAdd, closeCompose,
    updateCompose, toggleComposeChannel, submitCompose, toast, showToast,
  ]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useScheduler(): SchedulerCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useScheduler must be used within SchedulerProvider");
  return c;
}

export { PF };
