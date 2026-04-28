import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BadgeAlert,
  Banknote,
  BrainCircuit,
  Database,
  FileSearch,
  GitBranch,
  LayoutDashboard,
  Network,
  ShieldCheck,
  UploadCloud,
  UserRoundSearch
} from "lucide-react";
import "./styles.css";
import {
  caseInfo,
  collisionFindings,
  evidenceFiles,
  graphEdges,
  graphNodes,
  people,
  reports,
  transactions
} from "./mockData";

const navItems = [
  { id: "overview", label: "总览", icon: LayoutDashboard },
  { id: "evidence", label: "证据接入", icon: UploadCloud },
  { id: "graph", label: "图谱穿透", icon: Network },
  { id: "collision", label: "分析碰撞", icon: GitBranch },
  { id: "portrait", label: "信息画像", icon: UserRoundSearch },
  { id: "report", label: "报告建议", icon: FileSearch }
];

function RiskPill({ value }) {
  return <span className={`risk risk-${value}`}>{value}</span>;
}

function Sidebar({ active, setActive }) {
  return (
    <aside className="sidebar">
      <div className="brand-block">
        <div className="brand-mark">检</div>
        <div>
          <strong>检察侦查画像模型</strong>
          <span>Investigation Intelligence</span>
        </div>
      </div>
      <nav className="nav-list">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              className={active === item.id ? "active" : ""}
              key={item.id}
              onClick={() => setActive(item.id)}
              type="button"
            >
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>
      <div className="security-box">
        <ShieldCheck size={18} />
        <span>依法立案侦查后使用</span>
      </div>
    </aside>
  );
}

function Header({ active }) {
  const title = navItems.find((item) => item.id === active)?.label ?? "总览";
  return (
    <header className="app-header">
      <div>
        <span className="eyebrow">案件编号 {caseInfo.id}</span>
        <h1>{title}</h1>
      </div>
      <div className="case-status">
        <span>{caseInfo.status}</span>
        <strong>{caseInfo.date}</strong>
      </div>
    </header>
  );
}

function StatCard({ icon: Icon, label, value, hint }) {
  return (
    <article className="stat-card">
      <Icon size={22} />
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{hint}</small>
      </div>
    </article>
  );
}

function Overview() {
  return (
    <div className="page-grid">
      <section className="panel hero-panel">
        <div>
          <span className="eyebrow">当前案件</span>
          <h2>{caseInfo.name}</h2>
          <p>{caseInfo.summary}</p>
        </div>
        <div className="workflow">
          {["证据接入", "标准化", "图谱构建", "交叉碰撞", "画像建议"].map((step) => (
            <span key={step}>{step}</span>
          ))}
        </div>
      </section>
      <section className="stats-row">
        <StatCard icon={Database} label="证据文件" value="5" hint="多格式已接入" />
        <StatCard icon={UserRoundSearch} label="重点对象" value="5" hint="含1名核心嫌疑人" />
        <StatCard icon={Banknote} label="异常交易" value="4" hint="集中于关键窗口" />
        <StatCard icon={BadgeAlert} label="碰撞线索" value="4" hint="两项高风险" />
      </section>
      <section className="panel split-panel">
        <div>
          <span className="eyebrow">重点提示</span>
          <h3>资金、轨迹与通联在同一时间窗口重叠</h3>
          <p>系统将关系图谱、结构化流水、通联详单与时序记录共同组织，输出可疑资金流、异常行为和关系人画像。</p>
        </div>
        <div className="mini-timeline">
          {transactions.slice(0, 4).map((tx) => (
            <div key={tx.time}>
              <strong>{tx.time}</strong>
              <span>{tx.tag}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Evidence() {
  return (
    <div className="page-grid">
      <section className="panel upload-panel">
        <UploadCloud size={34} />
        <h2>拖拽或选择证据文件</h2>
        <p>支持 Word、PDF、Excel、CSV、OCR 文本、银行流水、通联记录、门禁日志等多源数据。</p>
        <button type="button">模拟导入证据包</button>
      </section>
      <section className="panel table-panel">
        <div className="panel-head">
          <span className="eyebrow">解析队列</span>
          <strong>字段标准化 / 来源标注 / 风险初筛</strong>
        </div>
        <table>
          <thead>
            <tr>
              <th>文件</th>
              <th>来源</th>
              <th>状态</th>
              <th>实体</th>
              <th>关系</th>
              <th>风险</th>
            </tr>
          </thead>
          <tbody>
            {evidenceFiles.map((file) => (
              <tr key={file.name}>
                <td>
                  <strong>{file.name}</strong>
                  <small>{file.type}</small>
                </td>
                <td>{file.source}</td>
                <td>{file.status}</td>
                <td>{file.entities}</td>
                <td>{file.relations}</td>
                <td><RiskPill value={file.risk} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function GraphView() {
  const nodeById = useMemo(() => Object.fromEntries(graphNodes.map((n) => [n.id, n])), []);
  return (
    <div className="graph-layout">
      <section className="panel graph-panel">
        <div className="panel-head">
          <span className="eyebrow">关系组织核心</span>
          <strong>人物 / 账户 / 企业 / 资金路径</strong>
        </div>
        <svg viewBox="0 0 900 460" className="graph-svg" role="img">
          {graphEdges.map((edge) => {
            const from = nodeById[edge.from];
            const to = nodeById[edge.to];
            return (
              <g key={`${edge.from}-${edge.to}`}>
                <line className={`edge ${edge.kind}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} />
                <text x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 7}>{edge.label}</text>
              </g>
            );
          })}
          {graphNodes.map((node) => (
            <g key={node.id} className={`node ${node.type}`}>
              <circle cx={node.x} cy={node.y} r={node.type === "suspect" ? 42 : 34} />
              <text x={node.x} y={node.y + 5}>{node.label}</text>
            </g>
          ))}
        </svg>
      </section>
      <aside className="panel detail-panel">
        <span className="eyebrow">穿透分析详情</span>
        <h3>企业X → 离岸账户</h3>
        <p>该路径同时命中资金流动、人物关系和关键时间窗口，建议作为优先复核链路。</p>
        <div className="detail-list">
          <span>穿透层级：二度</span>
          <span>关系类型：资金往来 / 通讯关联</span>
          <span>证据来源：银行流水、通联详单、企业登记</span>
        </div>
      </aside>
    </div>
  );
}

function Collision() {
  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-head">
          <span className="eyebrow">多维碰撞矩阵</span>
          <strong>人、钱、行、时交叉验证</strong>
        </div>
        <div className="collision-grid">
          {collisionFindings.map((item) => (
            <article key={item.title}>
              <div>
                <h3>{item.title}</h3>
                <RiskPill value={item.level} />
              </div>
              <p>{item.result}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="panel transaction-panel">
        <div className="panel-head">
          <span className="eyebrow">可疑资金窗口</span>
          <strong>04-06 至 04-10</strong>
        </div>
        {transactions.map((tx) => (
          <div className="transaction" key={`${tx.time}-${tx.amount}`}>
            <div>
              <strong>{tx.from} → {tx.to}</strong>
              <span>{tx.time} · {tx.tag}</span>
            </div>
            <b>¥{tx.amount.toLocaleString()}</b>
          </div>
        ))}
      </section>
    </div>
  );
}

function Portrait() {
  return (
    <div className="portrait-grid">
      {people.map((person) => (
        <article className={`portrait-card ${person.id === "p1" ? "primary" : ""}`} key={person.id}>
          <div className="avatar">{person.name.slice(0, 1)}</div>
          <div>
            <span>{person.role}</span>
            <h3>{person.name}</h3>
            <div className="risk-bar"><i style={{ width: `${person.risk}%` }} /></div>
            <strong>风险指数 {person.risk}</strong>
          </div>
          <div className="tag-row">
            {person.tags.map((tag) => <em key={tag}>{tag}</em>)}
          </div>
        </article>
      ))}
    </div>
  );
}

function Report() {
  return (
    <div className="report-layout">
      <section className="panel report-panel">
        <span className="eyebrow">专题报告生成</span>
        <h2>张某关系链与资金流动综合分析报告</h2>
        <p>系统基于图谱查询结果、碰撞结果和画像结果，生成面向侦查人员的结构化参考建议。</p>
        <div className="report-block">
          <h3>核心结论</h3>
          <p>张某与李某、王某之间存在资金、通联与时间窗口的多重重合，其中账户A至李某的分拆转账与后续企业X离岸转出形成连续链路。</p>
        </div>
      </section>
      <aside className="panel">
        <span className="eyebrow">参考建议</span>
        <div className="advice-list">
          {reports.map((item) => <div key={item}>{item}</div>)}
        </div>
      </aside>
    </div>
  );
}

function MainContent({ active }) {
  if (active === "evidence") return <Evidence />;
  if (active === "graph") return <GraphView />;
  if (active === "collision") return <Collision />;
  if (active === "portrait") return <Portrait />;
  if (active === "report") return <Report />;
  return <Overview />;
}

function App() {
  const [active, setActive] = useState("overview");

  return (
    <div className="app-shell">
      <Sidebar active={active} setActive={setActive} />
      <main className="workspace">
        <Header active={active} />
        <MainContent active={active} />
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
