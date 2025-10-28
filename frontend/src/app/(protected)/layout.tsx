// frontend/src/app/(protected)/layout.tsx

import { ProtectedClientLayout } from "./ProtectedClientLayout";

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // This is now a pure Server Component that renders our Client Component.
  return <ProtectedClientLayout>{children}</ProtectedClientLayout>;
}