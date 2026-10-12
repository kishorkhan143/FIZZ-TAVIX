import { createPortal } from 'react-dom';

/**
 * ModalPortal renders children directly into document.body.
 * This prevents CSS transform ancestor bugs (such as Framer Motion page transitions)
 * from trapping position: fixed elements and pushing modals down long pages.
 */
export default function ModalPortal({ children }) {
  if (typeof document === 'undefined') return null;
  return createPortal(children, document.body);
}
