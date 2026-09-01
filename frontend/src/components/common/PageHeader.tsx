import type { ReactNode } from 'react';

export function PageHeader({
  kicker,
  title,
  desc,
  extra,
}: {
  kicker?: string;
  title: ReactNode;
  desc?: ReactNode;
  extra?: ReactNode;
}) {
  return (
    <header className="om-page-header">
      <div className="om-page-header-text">
        {kicker ? <div className="om-kicker">{kicker}</div> : null}
        <h1 className="om-page-title">{title}</h1>
        {desc ? <p className="om-page-desc">{desc}</p> : null}
      </div>
      {extra ? <div className="om-page-header-extra">{extra}</div> : null}
    </header>
  );
}
