import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { motion } from "framer-motion";
import { CHANGELOG, formatChangelogDate } from "@/data/changelog";

export default function ChangelogPage() {
  return (
    <div className="max-w-2xl mx-auto w-full px-3 sm:px-4 py-4 sm:py-8 space-y-5 sm:space-y-6">
      <h1
        className="font-heading font-extrabold text-2xl sm:text-3xl text-center"
        data-testid="changelog-title"
      >
        Changelog
      </h1>

      <div className="space-y-4 sm:space-y-5">
        {CHANGELOG.map((entry, i) => (
          <motion.div
            key={`${entry.date}-${entry.title}`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.05, 0.3) }}
          >
            <Card
              className="rounded-xl border border-border overflow-hidden"
              data-testid={`changelog-entry-${i}`}
            >
              <CardHeader className="flex flex-row items-start justify-between gap-3 border-b border-border/60 py-4">
                <h2 className="font-heading font-bold text-lg leading-tight">
                  {entry.title}
                </h2>
                <span className="font-technical text-xs sm:text-sm text-primary whitespace-nowrap pt-0.5">
                  {formatChangelogDate(entry.date)}
                </span>
              </CardHeader>
              <CardContent className="py-4 space-y-3">
                {entry.body.map((paragraph, p) => (
                  <p
                    key={`p-${p}`}
                    className="text-sm sm:text-[15px] text-foreground/80 leading-relaxed"
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
