import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { Button } from "@/components/ui/button"; // <-- Import our new Shadcn Button

export default function Home() {
  return (
    <main>
      <header className="flex justify-between items-center p-4 border-b">
        <h1 className="text-2xl font-bold">
          <Link href="/">AI Finance Planner</Link>
        </h1>
        <div>
          <SignedIn>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
          <SignedOut>
            <div className="flex items-center gap-4">
              {/* The "mode='modal'" from Clerk will open the sign-in flow in a popup */}
              <SignInButton mode="modal">
                <Button variant="ghost">Sign In</Button>
              </SignInButton>
              <SignUpButton mode="modal">
                 <Button>Sign Up</Button>
              </SignUpButton>
            </div>
          </SignedOut>
        </div>
      </header>

      <div className="p-8 text-center">
        <SignedIn>
          <h2 className="text-3xl font-semibold mb-4">Welcome back!</h2>
          <p className="mb-8">You are now ready to manage your finances.</p>
          <Button asChild>
            <Link href="/dashboard">Go to Dashboard</Link>
          </Button>
        </SignedIn>
        <SignedOut>
          <h2 className="text-3xl font-semibold mb-4">Get Clarity on Your Finances</h2>
          <p className="mb-8">Upload your statements and let our secure AI do the rest. Sign up to get started.</p>
          <SignUpButton mode="modal">
            <Button size="lg">Get Started for Free</Button>
          </SignUpButton>
        </SignedOut>
      </div>
    </main>
  );
}