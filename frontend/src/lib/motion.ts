import { Variants } from "framer-motion";

export const pageMotionVariants: Variants = {
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.22, ease: "easeOut" } },
  exit: { opacity: 0, y: -4, transition: { duration: 0.15, ease: "easeIn" } },
};

export const cardMotionVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: (i: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.28,
      delay: i * 0.045,
      ease: "easeOut",
    },
  }),
};

export const tabIndicatorTransition = {
  type: "spring",
  stiffness: 400,
  damping: 30,
};
