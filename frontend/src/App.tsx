import { lazy, useEffect, useState, type ComponentType } from "react";
import { Routes, Route } from "react-router-dom";
import AlertProvider from "./components/ui/AlertProvider";
import WelcomeModal from "./components/ui/WelcomeModal";
import AppLayout from "./components/layout/AppLayout";
// Workbench 是默认落地页，保持同步加载，避免首屏空窗
import Workbench from "./pages/Workbench";
import { ensureControlSession, type ControlUser } from "./api/controlPlane";
import LocalLoginDialog from "./components/LocalLoginDialog";
import { useControlStore } from "./stores/controlStore";
import { useSubscriptionStore } from "./stores/subscriptionStore";

// 命名导出模块的懒加载包装（React.lazy 只接受 default 导出）
const lazyNamed = <T,>(loader: () => Promise<T>, exportName: keyof T) =>
  lazy(async () => ({ default: (await loader())[exportName] as ComponentType<unknown> }));

// 路由级懒加载：首屏只拉取「布局外壳 + Workbench」，其余模块进入时按需加载。
// 每个 lazy() 会被打包成独立 chunk，与 vite.config 的依赖分包叠加后，
// 首屏 JS 体积与解析成本大幅下降（未访问的页面不进入内存）。
const BatchWorkshop = lazy(() => import("./pages/BatchWorkshop"));
const History = lazy(() => import("./pages/History"));
const Settings = lazy(() => import("./pages/Settings"));
const About = lazy(() => import("./pages/About"));
const Logs = lazy(() => import("./pages/Logs"));
const SocialPublish = lazy(() => import("./pages/SocialPublish"));
const LLMRouter = lazy(() => import("./pages/llm-router"));
const EditingWorkbench = lazy(() => import("./pages/EditingWorkbench"));
const MaterialLibrary = lazy(() => import("./pages/MaterialLibrary"));
const CreationCanvas = lazy(() => import("./pages/creation-canvas/CreationCanvas"));
const Collaboration = lazy(() => import("./pages/Collaboration"));
const Community = lazy(() => import("./pages/Community"));
const Guide = lazy(() => import("./pages/Guide"));

// VoiceForge 的多个导出来自同一模块，复用同一个 loader 保证落在同一 chunk
const loadVoiceForge = () => import("./pages/VoiceForge");
const VoiceForgeHome = lazyNamed(loadVoiceForge, "VoiceForgeHome");
const VoiceForgeWorkspace = lazyNamed(loadVoiceForge, "VoiceForgeWorkspace");
const VoiceForgeVoices = lazyNamed(loadVoiceForge, "VoiceForgeVoices");
const VoiceForgeAssets = lazyNamed(loadVoiceForge, "VoiceForgeAssets");
const VoiceForgeSettings = lazyNamed(loadVoiceForge, "VoiceForgeSettings");
const VoiceForgeLayout = lazyNamed(() => import("./components/voiceforge/VoiceForgeLayout"), "VoiceForgeLayout");
const SceneDesignPlaceholder = lazyNamed(() => import("./components/voiceforge/VoiceForgePlaceholders"), "SceneDesignPlaceholder");
const VideoDubbingPage = lazyNamed(() => import("./components/voiceforge/videodub/VideoDubbingPage"), "VideoDubbingPage");

function applyUISettings() {
  try {
    const theme = JSON.parse(localStorage.getItem("vl_theme") || '"system"');
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    if (theme === "system") {
      root.classList.add(window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    } else {
      root.classList.add(theme);
    }

    const fontScale = JSON.parse(localStorage.getItem("vl_font_scale") || '"medium"');
    const sizes: Record<string, string> = { small: "14px", medium: "15px", large: "16px", xlarge: "18px" };
    if (sizes[fontScale]) document.documentElement.style.fontSize = sizes[fontScale];

    const fontFamily = JSON.parse(localStorage.getItem("vl_font_family") || '"plus-jakarta"');
    // Map old keys to new values for backward compatibility
    const familyMap: Record<string, string> = {
      default: '"Plus Jakarta Sans", system-ui, sans-serif',
      serif: '"Noto Serif", Georgia, serif',
      mono: '"JetBrains Mono", "Fira Code", monospace',
      "plus-jakarta": '"Plus Jakarta Sans", system-ui, sans-serif',
      inter: '"Inter", system-ui, sans-serif',
      "noto-sans": '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
      roboto: '"Roboto", system-ui, sans-serif',
      "source-han-sans": '"Source Han Sans SC", "Noto Sans SC", sans-serif',
      "noto-serif": '"Noto Serif", Georgia, serif',
      playfair: '"Playfair Display", Georgia, serif',
      merriweather: '"Merriweather", Georgia, serif',
      "jetbrains-mono": '"JetBrains Mono", "Fira Code", monospace',
      "fira-code": '"Fira Code", "Cascadia Code", monospace',
      system: "ui-sans-serif, system-ui, sans-serif",
    };
    if (familyMap[fontFamily]) document.body.style.fontFamily = familyMap[fontFamily];

    const mesh = JSON.parse(localStorage.getItem("vl_mesh_gradient") ?? "true");
    document.querySelector(".gradient-mesh")?.classList.toggle("no-mesh", !mesh);

    const reduceMotion = JSON.parse(localStorage.getItem("vl_reduce_motion") || "false");
    if (reduceMotion) document.documentElement.style.setProperty("--animation-duration", "0s");

    const navIcons = JSON.parse(localStorage.getItem("vl_nav_icons") ?? "true");
    document.body.classList.toggle("nav-icons-hidden", !navIcons);
  } catch {}
}

export default function App() {
  // 免密会话建立失败时要求手动登录：容器化/公网访问下来源不是环回地址，
  // local-session 返回 403，缺少登录入口会导致所有接口 401、界面看着「跑不动」。
  const [needLogin, setNeedLogin] = useState(false);

  useEffect(() => {
    applyUISettings();
    // 启动期确保控制面会话：环回自动登录，未初始化则自动 bootstrap 默认管理员
    ensureControlSession()
      .then((user) => {
        if (user) useControlStore.getState().setUser(user);
        else setNeedLogin(true);
      })
      .catch(() => setNeedLogin(true));
    useSubscriptionStore.getState().fetchStatus().catch(() => undefined);
  }, []);

  const handleLoggedIn = (user: ControlUser) => {
    useControlStore.getState().setUser(user);
    setNeedLogin(false);
    // 登录前拿不到数据的页面需要重新取一次状态
    useSubscriptionStore.getState().fetchStatus().catch(() => undefined);
  };

  return (
    <AlertProvider>
      {needLogin && <LocalLoginDialog onSuccess={handleLoggedIn} />}
      <WelcomeModal />
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Workbench />} />
          <Route path="/batch" element={<BatchWorkshop />} />
          <Route path="/history" element={<History />} />
          <Route path="/social" element={<SocialPublish />} />
          <Route path="/editing" element={<EditingWorkbench />} />
          <Route path="/materials" element={<MaterialLibrary />} />
          <Route path="/creation-canvas" element={<CreationCanvas />} />
          <Route path="/voiceforge" element={<VoiceForgeLayout />}>
            <Route index element={<VoiceForgeHome />} />
            <Route path="projects/:projectId" element={<VoiceForgeWorkspace />} />
            <Route path="voices" element={<VoiceForgeVoices />} />
            <Route path="assets" element={<VoiceForgeAssets />} />
            <Route path="settings" element={<VoiceForgeSettings />} />
            <Route path="video-dub" element={<VideoDubbingPage />} />
            <Route path="scene-design" element={<SceneDesignPlaceholder />} />
          </Route>
          <Route path="/settings" element={<Settings />} />
          <Route path="/llm-router" element={<LLMRouter />} />
          <Route path="/collaboration" element={<Collaboration />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/about" element={<About />} />
          <Route path="/community" element={<Community />} />
          <Route path="/guide" element={<Guide />} />
        </Route>
      </Routes>
    </AlertProvider>
  );
}
