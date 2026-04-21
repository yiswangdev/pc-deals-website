// "use client";

// import Link from "next/link";
// import { Settings, Lock, LogIn } from "lucide-react";
// import EmailAlertsPanel from "@/components/EmailAlertsPanel";
// import { useAuth } from "@/context/AuthContext";

// export default function SettingsPage() {
//   const { user, loading } = useAuth();

//   if (loading) {
//     return (
//       <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
//         <div
//           className="cyber-card rounded-none p-6 animate-fade-up opacity-0"
//           style={{ animationFillMode: "forwards" }}
//         >
//           <div className="skeleton h-4 w-40 mb-4 rounded" />
//           <div className="skeleton h-24 rounded" />
//         </div>
//       </div>
//     );
//   }

//   if (!user) {
//     return (
//       <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
//         <div
//           className="cyber-card rounded-none p-6 animate-fade-up opacity-0"
//           style={{ animationFillMode: "forwards" }}
//         >
//           <div className="flex items-center gap-2 mb-3">
//             <Lock size={14} className="text-cyber-cyan" />
//             <span className="font-mono text-xs text-cyber-muted tracking-widest">
//               ACCESS_CONTROL
//             </span>
//           </div>

//           <h1 className="font-orbitron text-2xl font-bold text-white tracking-wider">
//             SETTINGS <span className="text-cyber-cyan text-glow-cyan">LOCKED</span>
//           </h1>

//           <p className="font-mono text-xs text-cyber-muted mt-3">
//             Login required to configure alerts and notification settings.
//           </p>

//           <Link href="/login" className="btn-cyber inline-flex items-center gap-2 mt-5">
//             <LogIn size={12} />
//             LOGIN
//           </Link>
//         </div>
//       </div>
//     );
//   }

//   return (
//     <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-6">
//       <div className="animate-fade-up opacity-0" style={{ animationFillMode: "forwards" }}>
//         <div className="flex items-center gap-2 mb-1">
//           <Settings size={13} className="text-cyber-cyan" />
//           <span className="font-mono text-xs text-cyber-muted tracking-widest">
//             SYS_CONFIG
//           </span>
//         </div>
//         <h1 className="font-orbitron text-2xl font-bold text-white tracking-wider">
//           SYSTEM <span className="text-cyber-cyan text-glow-cyan">SETTINGS</span>
//         </h1>
//       </div>

//       <div
//         className="animate-fade-up opacity-0"
//         style={{ animationDelay: "100ms", animationFillMode: "forwards" }}
//       >
//         <EmailAlertsPanel />
//       </div>
//     </div>
//   );
// }
