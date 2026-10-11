import { Link } from "react-router-dom";

import { ErrorState } from "../components/ui";
import { useDocumentTitle } from "../lib/hooks";

export function NotFoundPage() {
  useDocumentTitle("Страница не найдена");
  return (
    <ErrorState title="Такой страницы нет" alert={false} level={1}>
      <p>
        Возможно, ссылка устарела. <Link to="/">На главную — к поиску технологий</Link>
      </p>
    </ErrorState>
  );
}
