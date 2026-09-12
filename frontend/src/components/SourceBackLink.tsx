import { Link, useLocation } from "react-router-dom";
import { detailReturnPaths, getReturnNavigation } from "../pages/m3Utils";

export function SourceBackLink({
  fallbackPath,
  fallbackLabel,
}: {
  fallbackPath: string;
  fallbackLabel: string;
}) {
  const location = useLocation();
  const navigation = getReturnNavigation(
    location.state,
    fallbackPath,
    fallbackLabel,
    detailReturnPaths,
  );
  return (
    <p>
      <Link className="m3-link" to={navigation.path} state={navigation.state}>
        ← {navigation.label}
      </Link>
    </p>
  );
}
