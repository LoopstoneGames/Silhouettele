import { motion, AnimatePresence } from "framer-motion";

export const BuildingDetails = ({ gameOver, building }) => (
  <AnimatePresence>
    {gameOver && building && (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.4 }}
        className="bento p-5 space-y-4"
        data-testid="building-details-card"
      >
        <div className="grid grid-cols-2 gap-4">
          {building.height_m > 0 && (
            <div className="space-y-0.5">
              <p className="font-technical text-[10px] text-muted-foreground uppercase tracking-[0.15em]">Height</p>
              <p className="font-heading font-bold text-lg">{building.height_m}m</p>
            </div>
          )}
          {building.year_built && (
            <div className="space-y-0.5">
              <p className="font-technical text-[10px] text-muted-foreground uppercase tracking-[0.15em]">Built</p>
              <p className="font-heading font-bold text-lg">
                {building.year_built < 0 ? `${Math.abs(building.year_built)} BC` : building.year_built}
              </p>
            </div>
          )}
        </div>
        {building.fun_fact && (
          <div className="space-y-1 border-t border-border pt-3">
            <p className="font-technical text-[10px] text-muted-foreground uppercase tracking-[0.15em]">Did you know?</p>
            <p className="text-sm text-foreground/80 leading-relaxed">{building.fun_fact}</p>
          </div>
        )}
      </motion.div>
    )}
  </AnimatePresence>
);
