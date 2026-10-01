/**
 * 控制面登录框：启动期无法免密建立会话时弹出，要求输入账号密码。
 *
 * 什么时候会出现：免密路径（/api/control/auth/local-session）只信任环回地址，
 * 容器化部署或从公网访问时来源不是 127.0.0.1，会返回 403，此时必须手动登录。
 * 默认账号见 backend/auth/local_account.py（启动时播种），密码不写在前端代码里，
 * 以免被打进公开的 JS 产物与镜像。
 */
import { useState } from "react";
import { LogIn } from "lucide-react";
import { loginControlSession } from "@/api/controlPlane";
import type { ControlUser } from "@/api/controlPlane";

interface Props {
  onSuccess: (user: ControlUser) => void;
}

export default function LocalLoginDialog({ onSuccess }: Props) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!username.trim() || !password) {
      setError("请输入用户名和密码");
      return;
    }
    setBusy(true);
    setError("");
    try {
      onSuccess(await loginControlSession(username.trim(), password));
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "object" ? detail?.message || "登录失败" : detail || "登录失败，请检查用户名和密码");
    } finally {
      setBusy(false);
    }
  };

  const field = "w-full px-3 py-2 text-sm rounded-lg border border-border/60 bg-background outline-none transition-all focus:border-primary/50 focus:ring-1 focus:ring-primary/20";

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <form onSubmit={submit} className="w-[360px] rounded-xl border border-border/60 bg-card p-6 shadow-xl">
        <div className="mb-1 flex items-center gap-2 text-base font-medium">
          <LogIn className="h-[18px] w-[18px]" />
          登录云智AI
        </div>
        <p className="mb-5 text-xs text-muted-foreground">本机直接运行时会自动登录；通过服务器或公网访问需要输入账号密码。</p>
        <label className="mb-1 block text-xs text-muted-foreground" htmlFor="local-login-username">用户名</label>
        <input id="local-login-username" className={`${field} mb-3`} value={username} autoComplete="username"
               onChange={(e) => setUsername(e.target.value)} disabled={busy} />
        <label className="mb-1 block text-xs text-muted-foreground" htmlFor="local-login-password">密码</label>
        <input id="local-login-password" className={field} type="password" value={password} autoComplete="current-password"
               onChange={(e) => setPassword(e.target.value)} disabled={busy} autoFocus />
        {error && <p role="alert" className="mt-3 text-xs text-destructive">{error}</p>}
        <button type="submit" disabled={busy}
                className="mt-5 w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50">
          {busy ? "登录中…" : "登录"}
        </button>
      </form>
    </div>
  );
}
