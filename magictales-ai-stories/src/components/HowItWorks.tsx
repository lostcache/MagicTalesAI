import { BookOpen, Mic, Headphones } from "lucide-react";

const steps = [
  {
    icon: BookOpen,
    title: "Select Your Story",
    description: "Choose which story you'd like to narrate from our ever-growing list of titles.",
  },
  {
    icon: Mic,
    title: "Record Your Narration",
    description: "Follow the on-screen prompts to add your voice—and even a personalized message!",
  },
  {
    icon: Headphones,
    title: "Get Your Audio Book",
    description: "Get your audiobook with multiple characters and different background music.",
  },
];

const HowItWorks = () => {
  return (
    <section className="py-20 px-4 bg-background">
      <div className="max-w-5xl mx-auto text-center">
        <h2 className="font-display font-extrabold text-3xl sm:text-4xl text-foreground mb-3">
          Unleash Your Inner Storyteller
        </h2>
        <p className="font-body text-muted-foreground text-lg mb-14 max-w-xl mx-auto">
          Connect with anyone, anywhere through the power of story.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-10">
          {steps.map(({ icon: Icon, title, description }) => (
            <div key={title} className="flex flex-col items-center gap-4">
              <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center">
                <Icon className="w-10 h-10 text-primary" />
              </div>
              <h3 className="font-display font-bold text-lg text-primary">{title}</h3>
              <p className="font-body text-muted-foreground text-sm leading-relaxed max-w-xs">
                {description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
