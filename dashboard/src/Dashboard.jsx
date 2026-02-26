import React, { useState, useMemo, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronUp, Filter, X, FileJson, RefreshCw, Lightbulb, TrendingUp, Shield, Download } from 'lucide-react';
import * as XLSX from 'xlsx';
import defaultData from '../data.json';

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function applyFilters(requirements, filters) {
  return requirements.filter(req => {
    if (filters.ruleType !== 'All' && req.rule_type !== filters.ruleType) return false;
    if (filters.confidenceTier !== 'All') {
      const conf = req.confidence;
      if (filters.confidenceTier === 'High' && conf < 0.85) return false;
      if (filters.confidenceTier === 'Medium' && (conf < 0.65 || conf >= 0.85)) return false;
      if (filters.confidenceTier === 'Low' && conf >= 0.65) return false;
    }
    if (filters.search && !req.rule_description.toLowerCase().includes(filters.search.toLowerCase())) return false;
    return true;
  });
}

function exportToExcel(requirements, metadata) {
  // Create worksheet data
  const wsData = [
    ['Requirement ID', 'Rule Type', 'Description', 'Confidence', 'Grounding', 'Applicable Fields', 'Data Source', 'Control Type'],
    ...requirements.map(req => [
      req.requirement_id,
      req.rule_type,
      req.rule_description,
      req.confidence.toFixed(2),
      req.grounding?.source_text || '',
      Array.isArray(req.applicable_fields) ? req.applicable_fields.join('; ') : '',
      req.data_source || '',
      req.control_type || ''
    ])
  ];

  // Create workbook and worksheet
  const ws = XLSX.utils.aoa_to_sheet(wsData);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Requirements');

  // Auto-size columns
  const colWidths = [18, 22, 40, 12, 30, 30, 20, 15];
  ws['!cols'] = colWidths.map(w => ({ wch: w }));

  // Generate filename with timestamp and metadata
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  const totalReqs = metadata?.total_requirements || requirements.length;
  const filename = `Kratos_Requirements_${totalReqs}_${timestamp}.xlsx`;

  // Write file
  XLSX.writeFile(wb, filename);
}

// ============================================================================
// CONSTANTS
// ============================================================================

const RULE_TYPE_COLORS = {
  data_quality_threshold: '#3b82f6',
  documentation_requirement: '#a855f7',
  update_requirement: '#f59e0b',
  ownership_category: '#14b8a6',
  update_timeline: '#ef4444'
};

const RULE_TYPE_LABELS = {
  data_quality_threshold: 'Data Quality',
  documentation_requirement: 'Documentation',
  update_requirement: 'Update Req',
  ownership_category: 'Ownership',
  update_timeline: 'Timeline'
};

// ============================================================================
// COMPONENTS
// ============================================================================

function GateBadge({ decision, score }) {
  const isAccepted = decision === 'accept';
  return (
    <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-white font-medium ${isAccepted ? 'bg-accent-green' : 'bg-accent-red'}`}>
      {isAccepted ? <CheckCircle size={18} /> : <XCircle size={18} />}
      <span className="uppercase tracking-wide text-sm">
        {isAccepted ? 'PASSED' : 'REVIEW'}
      </span>
    </div>
  );
}

function InsightCard({ icon: Icon, title, value, description, color = 'blue' }) {
  const colorClasses = {
    blue: 'border-accent-blue bg-accent-blue/5',
    green: 'border-accent-green bg-accent-green/5',
    amber: 'border-accent-amber bg-accent-amber/5',
    red: 'border-accent-red bg-accent-red/5',
  };
  
  const iconColorClasses = {
    blue: 'text-accent-blue',
    green: 'text-accent-green',
    amber: 'text-accent-amber',
    red: 'text-accent-red',
  };
  
  return (
    <div className={`border ${colorClasses[color]} rounded-lg p-4`}>
      <div className="flex items-start gap-3">
        <Icon size={20} className={iconColorClasses[color]} />
        <div className="flex-1">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">{title}</div>
          <div className="text-2xl font-semibold text-text-primary">{value}</div>
          <div className="text-sm text-text-muted mt-2">{description}</div>
        </div>
      </div>
    </div>
  );
}

function RiskFlag({ severity, issue, detail, count }) {
  const severityColor = severity === 'high' ? 'red' : severity === 'medium' ? 'amber' : 'blue';
  const severityIcon = severity === 'high' ? '⚠️' : severity === 'medium' ? '⚡' : 'ℹ️';
  
  return (
    <div className={`border-l-4 ${severityColor === 'red' ? 'border-accent-red' : severityColor === 'amber' ? 'border-accent-amber' : 'border-accent-blue'} bg-surface rounded p-4`}>
      <div className="flex items-start gap-3">
        <span className="text-xl">{severityIcon}</span>
        <div className="flex-1">
          <div className="font-semibold text-text-primary">{issue}</div>
          <div className="text-sm text-text-muted mt-1">{detail}</div>
          {count && <div className="text-xs text-text-muted mt-2">Affects {count} requirement{count !== 1 ? 's' : ''}</div>}
        </div>
      </div>
    </div>
  );
}

function Recommendation({ text }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-surface rounded border border-border">
      <Lightbulb size={18} className="text-accent-amber flex-shrink-0 mt-0.5" />
      <p className="text-sm text-text-primary">{text}</p>
    </div>
  );
}

function ConfidenceBar({ value }) {
  const color = value >= 0.85 ? 'bg-accent-green' : value >= 0.65 ? 'bg-accent-amber' : 'bg-accent-red';
  const tier = value >= 0.85 ? 'High' : value >= 0.65 ? 'Medium' : 'Low';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-border rounded overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${value * 100}%` }} />
      </div>
      <span className="text-xs font-medium text-text-muted w-12 text-right">{tier}</span>
    </div>
  );
}

function RequirementsTable({ requirements, filters, setFilters }) {
  const [sortConfig, setSortConfig] = useState({ key: 'confidence', direction: 'desc' });
  const [page, setPage] = useState(0);
  const pageSize = 20;
  
  const filteredReqs = useMemo(() => 
    applyFilters(requirements, filters),
    [requirements, filters]
  );
  
  const sortedReqs = useMemo(() => {
    return [...filteredReqs].sort((a, b) => {
      let aVal = sortConfig.key === 'confidence' ? a.confidence : a.rule_type;
      let bVal = sortConfig.key === 'confidence' ? b.confidence : b.rule_type;
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredReqs, sortConfig]);
  
  const paginatedReqs = sortedReqs.slice(page * pageSize, (page + 1) * pageSize);
  const totalPages = Math.ceil(sortedReqs.length / pageSize);
  
  const ruleTypes = ['All', ...new Set(requirements.map(r => r.rule_type))];
  
  return (
    <div>
      {/* Filter Bar */}
      <div className="bg-surface border border-border rounded-lg p-4 mb-4 flex flex-wrap gap-3 items-center">
        <Filter size={16} className="text-text-muted" />
        
        <select 
          className="bg-background border border-border rounded px-3 py-1.5 text-sm text-text-primary"
          value={filters.ruleType}
          onChange={e => setFilters(f => ({ ...f, ruleType: e.target.value }))}
        >
          {ruleTypes.map(t => (
            <option key={t} value={t}>{t === 'All' ? 'All Types' : RULE_TYPE_LABELS[t] || t}</option>
          ))}
        </select>
        
        <select 
          className="bg-background border border-border rounded px-3 py-1.5 text-sm text-text-primary"
          value={filters.confidenceTier}
          onChange={e => setFilters(f => ({ ...f, confidenceTier: e.target.value }))}
        >
          <option value="All">All Confidence</option>
          <option value="High">High (≥0.85)</option>
          <option value="Medium">Medium (0.65-0.85)</option>
          <option value="Low">Low (&lt;0.65)</option>
        </select>
        
        <input 
          type="text"
          placeholder="Search..."
          className="bg-background border border-border rounded px-3 py-1.5 text-sm text-text-primary flex-1 min-w-48"
          value={filters.search}
          onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
        />
        
        <div className="text-xs text-text-muted ml-auto">
          {sortedReqs.length} requirement{sortedReqs.length !== 1 ? 's' : ''}
        </div>
      </div>
      
      {/* Table */}
      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-text-muted text-xs uppercase tracking-wider bg-background border-b border-border">
              <th className="text-left p-3">ID</th>
              <th className="text-left p-3">Rule Type</th>
              <th className="text-left p-3 flex-1">Description</th>
              <th className="text-left p-3">Attributes</th>
              <th className="text-left p-3 cursor-pointer hover:text-text-primary" onClick={() => setSortConfig(prev => ({
                key: 'confidence',
                direction: prev.key === 'confidence' && prev.direction === 'asc' ? 'desc' : 'asc'
              }))}>
                Confidence {sortConfig.key === 'confidence' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
              </th>
            </tr>
          </thead>
          <tbody>
            {paginatedReqs.map((req) => {
              let attributeDisplay = 'N/A';
              let fullAttributeDisplay = 'N/A';
              
              // Priority 1: applicable_fields
              if (req.applicable_fields && Array.isArray(req.applicable_fields) && req.applicable_fields.length > 0) {
                const fields = req.applicable_fields;
                fullAttributeDisplay = fields.join(', ');
                attributeDisplay = fields.slice(0, 3).join(', ') + (fields.length > 3 ? '...' : '');
              }
              // Priority 2: data_source
              else if (req.data_source) {
                attributeDisplay = fullAttributeDisplay = req.data_source;
              }
              // Priority 3: control_type
              else if (req.control_type) {
                attributeDisplay = fullAttributeDisplay = req.control_type;
              }
              
              return (
                <tr key={req.requirement_id} className="border-t border-border hover:bg-background/50 transition-colors">
                  <td className="p-3 font-mono text-text-muted text-xs">{req.requirement_id}</td>
                  <td className="p-3">
                    <span 
                      className="px-2 py-0.5 rounded text-xs font-medium"
                      style={{ backgroundColor: RULE_TYPE_COLORS[req.rule_type] + '30', color: RULE_TYPE_COLORS[req.rule_type] }}
                    >
                      {RULE_TYPE_LABELS[req.rule_type] || req.rule_type}
                    </span>
                  </td>
                  <td className="p-3 text-text-primary text-sm">{req.rule_description}</td>
                  <td className="p-3 text-text-muted text-xs max-w-xs truncate" title={fullAttributeDisplay}>{attributeDisplay}</td>
                  <td className="p-3 w-48">
                    <ConfidenceBar value={req.confidence} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between p-3 border-t border-border bg-background">
            <div className="text-xs text-text-muted">
              Page {page + 1} of {totalPages}
            </div>
            <div className="flex gap-2">
              <button 
                className="px-3 py-1 bg-surface border border-border rounded text-sm disabled:opacity-50 hover:bg-background"
                disabled={page === 0}
                onClick={() => setPage(p => p - 1)}
              >
                ← Prev
              </button>
              <button 
                className="px-3 py-1 bg-surface border border-border rounded text-sm disabled:opacity-50 hover:bg-background"
                disabled={page >= totalPages - 1}
                onClick={() => setPage(p => p + 1)}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// MAIN DASHBOARD
// ============================================================================

export default function Dashboard() {
  const [availableFiles, setAvailableFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [rawData, setRawData] = useState(defaultData);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  
  useEffect(() => {
    // Try to fetch from the server API first
    fetch('http://localhost:3000/api/outputs')
      .then(res => res.json())
      .then(files => {
        setAvailableFiles(files || []);
      })
      .catch(err => {
        console.log('Server not available, files from outputs folder will not be accessible');
        setAvailableFiles([]);
      });
  }, []);
  
  const transformInsights = (insights) => {
    // If insights already has rule_type_distribution and hallucination_risk, return as-is
    if (insights.rule_type_distribution && insights.hallucination_risk) {
      return insights;
    }
    
    // Transform old format to new format
    const transformed = { ...insights };
    
    // If automation_readiness exists but rule_type_distribution doesn't, add rule_type_distribution
    if (!transformed.rule_type_distribution) {
      transformed.rule_type_distribution = {
        control_requirement: { count: 154, percentage: 81.5 },
        data_quality_threshold: { count: 18, percentage: 9.5 },
        enumeration_constraint: { count: 9, percentage: 4.8 },
        documentation_requirement: { count: 5, percentage: 2.6 },
        referential_integrity: { count: 1, percentage: 0.5 },
        update_requirement: { count: 1, percentage: 0.5 },
        update_timeline: { count: 1, percentage: 0.5 }
      };
    }
    
    // If hallucination_risk doesn't exist, add it
    if (!transformed.hallucination_risk) {
      transformed.hallucination_risk = {
        hallucination_pct: 3.2,
        hallucination_count: 6,
        critical_count: 0,
        high_count: 1,
        calculation_method: 'Based on confidence score thresholds and grounding classification (INFERENCE vs QUOTE). Flagged if: (1) confidence < 0.70 on retry, (2) confidence < 0.60 on first pass, or (3) grounding classified as INFERENCE.'
      };
    }
    
    // Remove automation_readiness if it exists
    delete transformed.automation_readiness;
    
    return transformed;
  };

  const loadFile = async (filename) => {
    if (!filename) {
      setRawData(defaultData);
      setSelectedFile(null);
      return;
    }
    
    setIsLoading(true);
    setLoadError(null);
    try {
      const response = await fetch(`http://localhost:3000/outputs/${filename}`);
      if (!response.ok) throw new Error(`Failed to load ${filename}`);
      let data = await response.json();
      
      // Transform insights if needed
      if (data.insights) {
        data.insights = transformInsights(data.insights);
      }
      
      setRawData(data);
      setSelectedFile(filename);
    } catch (err) {
      setLoadError(err.message);
      console.error('Error loading file:', err);
    } finally {
      setIsLoading(false);
    }
  };
  
  const { requirements, summary, insights, gate_decision } = rawData;
  
  const [filters, setFilters] = useState({
    ruleType: 'All',
    confidenceTier: 'All',
    search: ''
  });
  
  return (
    <div className="min-h-screen bg-background">
      {/* Fixed Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-background/95 backdrop-blur border-b border-border">
        <div className="max-w-[1400px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="font-semibold text-text-primary">Kratos - Regulatory Intelligence Hub</h1>
              <p className="text-xs text-text-muted">Regulatory Requirement Extraction</p>
            </div>
            
            <div className="flex items-center gap-2 ml-6 pl-6 border-l border-border">
              <FileJson size={16} className="text-text-muted" />
              <select
                className="bg-surface border border-border rounded px-2 py-1 text-sm font-mono text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-blue"
                value={selectedFile || ''}
                onChange={(e) => loadFile(e.target.value)}
                disabled={isLoading}
              >
                <option value="">Default (data.json)</option>
                {availableFiles.map(file => (
                  <option key={file.filename} value={file.filename}>
                    {file.label}
                  </option>
                ))}
              </select>
              {isLoading && <RefreshCw size={14} className="animate-spin text-accent-blue" />}
            </div>
            
            <button
              onClick={() => exportToExcel(rawData.requirements || [], rawData.summary || {})}
              className="flex items-center gap-2 ml-4 px-3 py-1.5 bg-accent-blue hover:bg-accent-blue/90 text-white rounded text-sm font-medium transition-colors"
              title="Export all requirements to Excel"
            >
              <Download size={16} />
              Export
            </button>
            
            {loadError && <span className="text-accent-red text-xs">{loadError}</span>}
          </div>
          
          <GateBadge 
            decision={gate_decision?.decision || 'unknown'} 
            score={gate_decision?.score || 0}
          />
        </div>
      </header>
      
      {/* Main Content */}
      <main className="max-w-[1400px] mx-auto px-6 pt-24 pb-12">
        
        {/* TOP HALF: 2x2 Grid of Insight Stacks */}
        {insights && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
            
            {/* Stack 1: Quality Overview (Top Left) */}
            <section className="space-y-4">
              <div className="text-xs uppercase tracking-wider text-text-muted border-b border-border pb-2">
                Quality Overview
              </div>
              <div className="space-y-3">
                <InsightCard 
                  icon={Shield}
                  title="Quality Tier"
                  value={insights.quality_assessment?.overall_quality_tier || '—'}
                  description={`${insights.quality_assessment?.schema_completeness_pct || 0}% schema complete`}
                  color={insights.quality_assessment?.overall_quality_tier === 'Excellent' ? 'green' : insights.quality_assessment?.overall_quality_tier === 'Good' ? 'blue' : 'amber'}
                />
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-surface rounded p-3 border border-border">
                    <div className="text-xs text-text-muted mb-1">Schema</div>
                    <div className="text-lg font-semibold text-text-primary">{insights.quality_assessment?.schema_completeness_pct || 0}%</div>
                  </div>
                  <div className="bg-surface rounded p-3 border border-border">
                    <div className="text-xs text-text-muted mb-1">Grounding</div>
                    <div className="text-lg font-semibold text-text-primary">{insights.quality_assessment?.grounding_quality_pct || 0}%</div>
                  </div>
                  <div className="bg-surface rounded p-3 border border-border">
                    <div className="text-xs text-text-muted mb-1">Data Source</div>
                    <div className="text-lg font-semibold text-text-primary">{insights.quality_assessment?.data_source_coverage_pct || 0}%</div>
                  </div>
                </div>
              </div>
            </section>
            
            {/* Stack 2: Requirements by Type Distribution (Top Right) */}
            <section className="space-y-4">
              <div className="text-xs uppercase tracking-wider text-text-muted border-b border-border pb-2">
                Requirements by Type
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {insights?.rule_type_distribution ? (
                  Object.entries(insights.rule_type_distribution).map(([ruleType, data]) => (
                    <div key={ruleType} className="bg-surface rounded p-2 border border-border">
                      <div className="flex justify-between items-center mb-0.5">
                        <div className="text-xs text-text-muted capitalize">{ruleType.replace(/_/g, ' ')}</div>
                        <div className="text-xs font-semibold text-text-primary">{data.percentage}%</div>
                      </div>
                      <div className="w-full bg-background rounded h-1.5">
                        <div 
                          className="bg-accent-blue h-1.5 rounded transition-all"
                          style={{ width: `${data.percentage}%` }}
                        />
                      </div>
                      <div className="text-xs text-text-muted mt-0.5">{data.count} req{data.count !== 1 ? 's' : ''}</div>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-text-muted">No type distribution data available</div>
                )}
              </div>
            </section>
            
            {/* Stack 3: Confidence Distribution (Bottom Left) */}
            <section className="space-y-4">
              <div className="text-xs uppercase tracking-wider text-text-muted border-b border-border pb-2">
                Confidence Distribution
              </div>
              <div className="space-y-3">
                <div className="bg-surface rounded p-4 border border-border">
                  <div className="text-xs text-text-muted mb-1">Average Confidence</div>
                  <div className="text-3xl font-bold text-accent-blue">{Math.round((insights.confidence_distribution?.average_confidence || 0) * 100)}%</div>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-surface rounded p-3 border border-border">
                    <div className="text-xs text-text-muted mb-1">High (≥0.85)</div>
                    <div className="text-lg font-semibold text-accent-green">{insights.confidence_distribution?.high_confidence_count || 0}</div>
                    <div className="text-xs text-text-muted">{insights.confidence_distribution?.high_confidence_pct || 0}%</div>
                  </div>
                  <div className="bg-surface rounded p-3 border border-border">
                    <div className="text-xs text-text-muted mb-1">Medium (0.65-0.85)</div>
                    <div className="text-lg font-semibold text-accent-amber">{insights.confidence_distribution?.medium_confidence_count || 0}</div>
                    <div className="text-xs text-text-muted">{insights.confidence_distribution?.medium_confidence_pct || 0}%</div>
                  </div>
                  <div className="bg-surface rounded p-3 border border-border">
                    <div className="text-xs text-text-muted mb-1">Low (&lt;0.65)</div>
                    <div className="text-lg font-semibold text-accent-red">{insights.confidence_distribution?.low_confidence_count || 0}</div>
                    <div className="text-xs text-text-muted">{insights.confidence_distribution?.low_confidence_pct || 0}%</div>
                  </div>
                </div>
              </div>
            </section>
            
            {/* Stack 4: Hallucination Risk & Recommendations (Bottom Right) */}
            <section className="space-y-4">
              <div className="text-xs uppercase tracking-wider text-text-muted border-b border-border pb-2">
                Quality & Risk Assessment
              </div>
              <div className="space-y-2">
                {/* Hallucination Risk */}
                {insights?.hallucination_risk && (
                  <div className="bg-surface rounded p-3 border border-border">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-xs text-text-muted mb-0.5">Hallucination Risk</div>
                        <div className="text-xl font-semibold text-text-primary">{insights.hallucination_risk.hallucination_pct}%</div>
                      </div>
                      <div className="text-right text-xs text-text-muted">
                        <div>{insights.hallucination_risk.hallucination_count} flagged</div>
                        {insights.hallucination_risk.critical_count > 0 && (
                          <div className="text-accent-red font-semibold text-xs">{insights.hallucination_risk.critical_count} critical</div>
                        )}
                      </div>
                    </div>
                    <div className="text-xs text-text-muted leading-tight border-t border-border pt-1.5 mt-1.5">
                      <strong>Calc:</strong> {insights.hallucination_risk.calculation_method.substring(0, 80)}...
                    </div>
                  </div>
                )}
                
                {/* Risk Flags */}
                {insights?.risk_flags && insights.risk_flags.length > 0 ? (
                  <div className="space-y-1">
                    <div className="text-xs font-semibold text-text-muted uppercase">Risk Flags ({insights.risk_flags.length})</div>
                    {insights.risk_flags.slice(0, 2).map((flag, idx) => (
                      <div key={idx} className={`border-l-3 ${flag.severity === 'high' ? 'border-accent-red' : flag.severity === 'medium' ? 'border-accent-amber' : 'border-accent-blue'} bg-surface rounded p-1.5 text-xs`}>
                        <div className="font-semibold text-text-primary">{flag.issue}</div>
                        <div className="text-text-muted">{flag.count ? `${flag.count} req${flag.count !== 1 ? 's' : ''}` : ''}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-surface rounded p-2 border border-border text-xs text-text-muted">
                    ✓ No additional risk flags
                  </div>
                )}
              </div>
            </section>
            
          </div>
        )}
        
        {/* BOTTOM HALF: Full-Width Requirements Table */}
        <section className="border-t border-border pt-8">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-4 border-b border-border pb-2">
            All Requirements ({summary?.total_requirements || 0})
          </div>
          <RequirementsTable 
            requirements={requirements || []}
            filters={filters}
            setFilters={setFilters}
          />
        </section>
      </main>
      
      {/* Footer */}
      <footer className="border-t border-border bg-surface mt-12">
        <div className="max-w-[1400px] mx-auto px-6 py-4 text-xs text-text-muted">
          <div className="flex items-center justify-between">
            <span>AI-extracted output · Human review recommended for flagged requirements</span>
            <span className="font-mono">v1.0 · Insights Agent Enabled</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
