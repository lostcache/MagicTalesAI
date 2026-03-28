import { useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import type { ProcessedStory } from "@/types/story";

const StudyCard = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const story = location.state?.story as ProcessedStory | undefined;

  if (!story) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <p className="text-muted-foreground font-body">No story data found.</p>
          <Button variant="outline" onClick={() => navigate("/create")}>
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Create
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-2xl animate-fade-up">
        <div className="relative overflow-hidden rounded-3xl border border-primary/20 bg-gradient-to-br from-primary/5 via-card to-accent/5 p-8 shadow-lg">
          {/* Decorative glow */}
          <div className="absolute -top-20 -right-20 w-40 h-40 rounded-full opacity-20" style={{ background: "radial-gradient(circle, hsl(var(--primary)), transparent)" }} />

          <div className="relative z-10 text-center mb-6">
            <h3 className="font-display font-extrabold text-2xl text-foreground mb-1">
              Congratulations!
            </h3>
            <p className="font-body text-sm text-muted-foreground">
              You finished <span className="font-semibold text-foreground">{story.title}</span>
            </p>
          </div>

          {/* Summary */}
          <div className="bg-background/60 backdrop-blur-sm rounded-2xl p-5 mb-4 border border-border/50">
            <h4 className="font-display font-bold text-sm text-foreground mb-2 uppercase tracking-wider">
              Story Summary
            </h4>
            <p className="font-body text-foreground/80 text-sm leading-relaxed">{story.summary}</p>
          </div>

          {/* Takeaways */}
          <div className="bg-background/60 backdrop-blur-sm rounded-2xl p-5 border border-border/50">
            <h4 className="font-display font-bold text-sm text-foreground mb-3 uppercase tracking-wider">
              Key Takeaways
            </h4>
            <ul className="space-y-2.5">
              {story.learningInsights.map((insight, i) => (
                <li key={i} className="flex items-start gap-2.5 font-body text-sm text-foreground/80">
                  <span className="mt-0.5 w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0 text-xs font-bold">
                    {i + 1}
                  </span>
                  {insight}
                </li>
              ))}
            </ul>
          </div>

          {/* Back button */}
          <div className="mt-6 flex justify-center">
            <Button variant="outline" onClick={() => navigate("/create")} className="font-body">
              <ArrowLeft className="w-4 h-4 mr-2" /> Create Another Audiobook
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudyCard;
