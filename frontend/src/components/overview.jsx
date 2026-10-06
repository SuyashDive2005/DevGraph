import { overviewMock } from "../data/overvie-data";

function Overview() {
  const { repo, stats, insights } = overviewMock;

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm text-slate-500">Repository overview</p>
        <h2 className="text-2xl font-semibold text-slate-900">{repo.name}</h2>
        <p className="mt-1 text-sm text-slate-500">
          {repo.branch} branch · {repo.language} · analyzed {repo.analyzedAt}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {stats.map((stat) => (
          <div key={stat.key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">{stat.label}</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {insights.map((insight) => (
          <article key={insight.key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-blue-600">{insight.title}</p>
            <h3 className="mt-3 font-semibold text-slate-900">{insight.headline}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-500">{insight.detail}</p>
            <span className="mt-4 inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
              {insight.tag}
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}

export default Overview;