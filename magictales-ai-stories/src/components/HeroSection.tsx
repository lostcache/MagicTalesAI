import { Button } from "@/components/ui/button";
import { Mic, Upload, Star, Music, MessageCircle, Theater } from "lucide-react";
import { Link } from "react-router-dom";
import heroBg from "@/assets/hero-bg.jpg";

const FloatingElement = ({
  children,
  className,
  style,
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) => (
  <div className={`absolute pointer-events-none select-none ${className}`} style={style}>
    {children}
  </div>
);

const HeroSection = () => {
  const features = [
    { icon: Theater, label: "Multi-character voices" },
    { icon: Music, label: "AI-generated music" },
    { icon: MessageCircle, label: "Ask questions anytime" },
  ];

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Background Image */}
      <div className="absolute inset-0">
        <img
          src={heroBg}
          alt="Magical storytelling scene"
          className="w-full h-full object-cover"
          width={1920}
          height={1080}
        />
        <div
          className="absolute inset-0"
          style={{ background: "var(--gradient-hero)" }}
        />
      </div>

      {/* Floating Elements */}
      <FloatingElement className="top-[15%] left-[8%] animate-float text-4xl opacity-70">
        ⭐
      </FloatingElement>
      <FloatingElement className="top-[25%] right-[10%] animate-float-slow text-3xl opacity-60">
        📖
      </FloatingElement>
      <FloatingElement className="bottom-[30%] left-[12%] animate-float-slow text-3xl opacity-50">
        🎵
      </FloatingElement>
      <FloatingElement className="top-[40%] right-[5%] animate-sparkle text-2xl opacity-60">
        ✨
      </FloatingElement>
      <FloatingElement className="bottom-[20%] right-[15%] animate-float text-3xl opacity-50">
        🎧
      </FloatingElement>
      <FloatingElement className="top-[10%] left-[40%] animate-sparkle text-xl opacity-40" style={{ animationDelay: "1s" } as React.CSSProperties}>
        ⭐
      </FloatingElement>

      {/* Content */}
      <div className="relative z-10 text-center px-4 max-w-4xl mx-auto">
        <h1
          className="font-display font-extrabold text-4xl sm:text-5xl md:text-6xl lg:text-7xl text-primary-foreground leading-tight mb-6 opacity-0 animate-fade-up"
        >
          Turn Any Story into a{" "}
          <span className="text-accent">Magical</span> Audiobook
        </h1>

        <p
          className="font-body text-lg sm:text-xl text-primary-foreground/85 max-w-2xl mx-auto mb-10 opacity-0 animate-fade-up"
          style={{ animationDelay: "0.2s" }}
        >
          Create immersive audiobooks with AI voices, music, and interactive
          storytelling for children.
        </p>

        {/* Buttons */}
        <div
          className="flex items-center justify-center mb-6 opacity-0 animate-fade-up"
          style={{ animationDelay: "0.4s" }}
        >
          <Button variant="magic" size="xl" asChild>
            <Link to="/create">
              <Mic className="w-5 h-5" />
              Start Your Audiobook
            </Link>
          </Button>
        </div>

        {/* Tagline */}
        <p
          className="text-primary-foreground/60 text-sm font-body mb-12 opacity-0 animate-fade-up"
          style={{ animationDelay: "0.5s" }}
        >
          No recording. No editing. Just magic. ✨
        </p>

        {/* Feature Highlights */}
        <div
          className="flex flex-col sm:flex-row items-center justify-center gap-6 sm:gap-10 opacity-0 animate-fade-up"
          style={{ animationDelay: "0.6s" }}
        >
          {features.map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-2 text-primary-foreground/80"
            >
              <div className="w-10 h-10 rounded-full bg-primary-foreground/15 backdrop-blur-sm flex items-center justify-center">
                <Icon className="w-5 h-5 text-accent" />
              </div>
              <span className="font-body text-sm font-medium">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent" />
    </section>
  );
};

export default HeroSection;
