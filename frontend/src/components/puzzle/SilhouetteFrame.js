import { Building2, MapPin } from "lucide-react";
import { motion } from "framer-motion";

export const SilhouetteFrame = ({ silhouetteUrl, gameOver, building }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.96 }}
    animate={{ opacity: 1, scale: 1 }}
    transition={{ duration: 0.6, ease: "circOut" }}
    className="bento overflow-hidden"
    data-testid="silhouette-card"
  >
    <div className="relative w-full aspect-square flex items-center justify-center bg-card p-6">
      {silhouetteUrl ? (
        <motion.img
          key={silhouetteUrl}
          src={silhouetteUrl}
          alt="Building silhouette"
          className="max-w-full max-h-full object-contain animate-float-slow"
          data-testid="silhouette-image"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        />
      ) : (
        <div className="text-center space-y-3">
          <Building2 className="w-24 h-24 mx-auto text-foreground/20" strokeWidth={1} />
        </div>
      )}
      {gameOver && building && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-card via-card/95 to-transparent px-5 pt-10 pb-4 text-center"
        >
          <h3 className="font-heading font-bold text-xl">{building.name}</h3>
          <div className="flex items-center justify-center gap-1.5 text-muted-foreground text-sm mt-0.5">
            <MapPin className="w-3.5 h-3.5" />
            <span>{building.city}, {building.country}</span>
          </div>
        </motion.div>
      )}
    </div>
  </motion.div>
);
