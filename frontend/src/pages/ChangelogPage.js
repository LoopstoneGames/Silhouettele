import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { motion } from "framer-motion";
import { CHANGELOG, formatChangelogDate } from "@/data/changelog";

export default function ChangelogPage() {
  return (
    <div className="max-w-lg mx-auto w-full px-3 sm:px-4 py-4 sm:py-8 space-y-4 sm:space-y-6">
      <h1
        className="font-heading font-extrabold text-2xl sm:text-3xl"
        data-testid="changelog-title"
      >
        Changelog
      </h1>

      <div className="space-y-4">
        {CHANGELOG.map((entry, i) => (
          <motion.div
            key={`${entry.date}-${entry.title}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.05, 0.3) }}
          >
            <Card
              className="rounded-xl border border-border"
              data-testid={`changelog-entry-${i}`}
            >
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center justify-between gap-3">
                  <span className="font-heading text-lg">{entry.title}</span>
                  <span className="font-technical text-xs text-primary whitespace-nowrap">
                    {formatChangelogDate(entry.date)}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2.5">
                {entry.body.map((paragraph, p) => (
                  <p
                    key={`p-${p}`}
                    className="text-sm text-foreground/70 leading-relaxed"
                  >
                    {paragraph}
                  </p>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
