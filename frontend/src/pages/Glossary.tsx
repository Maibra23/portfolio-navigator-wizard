import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FINANCE_GLOSSARY } from "@/lib/finance-glossary";

const entries = Object.entries(FINANCE_GLOSSARY);

export default function Glossary() {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return entries;
    const q = search.trim().toLowerCase();
    return entries.filter(
      ([, v]) =>
        v.title.toLowerCase().includes(q) ||
        v.description.toLowerCase().includes(q)
    );
  }, [search]);

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto px-4 md:px-6 py-6">
        <div className="flex items-center gap-4 mb-6">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/" className="flex items-center gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to wizard
            </Link>
          </Button>
        </div>
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold text-foreground">
            Finance terms glossary
          </h1>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Plain-language definitions for terms used in the portfolio wizard.
        </p>
        <Input
          type="search"
          placeholder="Search terms..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="mb-6"
          aria-label="Search glossary"
        />
        <ul className="space-y-4">
          {filtered.length === 0 ? (
            <li className="text-sm text-muted-foreground">
              No terms match your search.
            </li>
          ) : (
            filtered.map(([key, { title, description }]) => (
              <li
                key={key}
                className="rounded-lg border border-border bg-card p-4 shadow-sm"
              >
                <h2 className="font-semibold text-foreground mb-1">{title}</h2>
                <p className="text-sm text-muted-foreground">{description}</p>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
