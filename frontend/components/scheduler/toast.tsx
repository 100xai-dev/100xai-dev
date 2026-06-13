"use client";

import { useScheduler } from "@/lib/scheduler/context";

export default function Toast() {
  const { toast } = useScheduler();
  return (
    <div className={`toast${toast.show ? " show" : ""}${toast.ai ? " ai" : ""}`}>
      <div className="ti">✓</div>
      <span>{toast.msg}</span>
    </div>
  );
}
