'use client';

export interface FilterState {
  search: string;
  city: string;
  platform: string;
  jobType: 'all' | 'intern' | 'fulltime';
  timeRange: 'all' | '7d' | '30d' | '90d';
  minScore: number;
  sort: 'score' | 'salary' | 'time';
}

interface JobFilterProps {
  filter: FilterState;
  onChange: (filter: FilterState) => void;
  cities: string[];
  platforms: string[];
}

export default function JobFilter({ filter, onChange, cities, platforms }: JobFilterProps) {
  const update = (patch: Partial<FilterState>) =>
    onChange({ ...filter, ...patch });

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
      {/* Search */}
      <input
        type="text"
        placeholder="搜索职位/公司..."
        value={filter.search}
        onChange={(e) => update({ search: e.target.value })}
        className="h-9 w-48 rounded-lg border border-gray-200 px-3 text-[13px] outline-none transition focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
      />

      {/* City */}
      <select
        value={filter.city}
        onChange={(e) => update({ city: e.target.value })}
        className="h-9 rounded-lg border border-gray-200 px-2 text-[13px] outline-none transition focus:border-blue-400"
      >
        <option value="">全部城市</option>
        {cities.map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>

      {/* Platform */}
      <select
        value={filter.platform}
        onChange={(e) => update({ platform: e.target.value })}
        className="h-9 rounded-lg border border-gray-200 px-2 text-[13px] outline-none transition focus:border-blue-400"
      >
        <option value="">全部来源</option>
        {platforms.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      {/* Job type */}
      <select
        value={filter.jobType}
        onChange={(e) => update({ jobType: e.target.value as FilterState['jobType'] })}
        className="h-9 rounded-lg border border-gray-200 px-2 text-[13px] outline-none transition focus:border-blue-400"
      >
        <option value="all">全部类型</option>
        <option value="intern">实习</option>
        <option value="fulltime">全职</option>
      </select>

      {/* Time range */}
      <select
        value={filter.timeRange}
        onChange={(e) => update({ timeRange: e.target.value as FilterState['timeRange'] })}
        className="h-9 rounded-lg border border-gray-200 px-2 text-[13px] outline-none transition focus:border-blue-400"
      >
        <option value="all">全部时间</option>
        <option value="7d">近 7 天</option>
        <option value="30d">近 30 天</option>
        <option value="90d">近 3 个月</option>
      </select>

      {/* Min score */}
      <div className="flex items-center gap-2">
        <span className="text-[13px] text-gray-500">最低评分</span>
        <input
          type="range"
          min={0}
          max={10}
          step={0.5}
          value={filter.minScore}
          onChange={(e) => update({ minScore: parseFloat(e.target.value) })}
          className="h-1.5 w-24 cursor-pointer accent-blue-500"
        />
        <span className="w-8 text-center text-[13px] font-medium text-gray-700">
          {filter.minScore}
        </span>
      </div>

      {/* Sort */}
      <select
        value={filter.sort}
        onChange={(e) => update({ sort: e.target.value as FilterState['sort'] })}
        className="h-9 rounded-lg border border-gray-200 px-2 text-[13px] outline-none transition focus:border-blue-400"
      >
        <option value="score">评分排序</option>
        <option value="salary">薪资排序</option>
        <option value="time">时间排序</option>
      </select>
    </div>
  );
}
