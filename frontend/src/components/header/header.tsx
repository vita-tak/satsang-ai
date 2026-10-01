import { ThemeToggle } from "@/components/header/theme-toggle";

export function Header() {
  return (
    <header className="flex items-center justify-between px-6 pt-2 sm:px-8 sm:pt-4">
      <h1 translate="no" className="flex items-center gap-3 font-serif text-body text-ink">
        <span className="size-1.5 rounded-full bg-accent" aria-hidden="true" />
        Satsang
      </h1>
      <ThemeToggle />
    </header>
  );
}
