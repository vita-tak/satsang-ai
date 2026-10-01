import { Header } from "@/components/header/header";
import { Satsang } from "@/components/satsang";

export default function Home() {
  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <Satsang />
    </div>
  );
}
