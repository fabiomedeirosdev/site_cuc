import { Link } from "react-router-dom";

export default function SiteLink({ href, children, ...props }) {
  const internal = href?.startsWith("#") || (href?.startsWith("/") && !href.startsWith("//"));
  return internal
    ? <Link to={href} {...props}>{children}</Link>
    : <a href={href} {...props}>{children}</a>;
}
