import { Button } from "@/components/ui/button";
import { BookOpen, Sparkles } from "lucide-react";

const Navbar = () => {
  const navItems = ["Home", "Stories", "Create", "How it Works"];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-primary/80 backdrop-blur-md border-b border-primary-foreground/10">
      <div className="container mx-auto flex items-center justify-between h-16 px-4">
        {/* Logo */}
        <a href="/" className="text-primary-foreground font-display font-extrabold text-xl">
          MagicTales-AI
        </a>

        {/* Center Nav */}
        <div className="hidden md:flex items-center gap-1">
          {navItems.map((item) => (
            <Button key={item} variant="nav" size="sm">
              {item}
            </Button>
          ))}
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          <Button variant="nav" size="sm" className="hidden sm:inline-flex">
            Log In
          </Button>
          <Button variant="signup" size="sm">
            Sign Up
          </Button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
