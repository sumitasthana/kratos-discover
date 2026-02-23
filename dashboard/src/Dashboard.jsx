import React, { useState, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronUp, Filter, X } from 'lucide-react';
import rawData from '../data.json';

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function buildHallucinationIndex(evalReport) {
  const index = {};
  if (!evalReport?.hallucination_flags) return index;
  for (const flag of evalReport.hallucination_flags) {
    index[flag.req_id] = {
      risk: flag.risk,
      flags: flag.flags,
      confidence: flag.confidence
    };
  }
  return index;
}

function buildSchemaIndex(evalReport) {
  const index = {};
  if (!evalReport?.schema_compliance_issues) return index;
  for (const issue of evalReport.schema_compliance_issues) {
    index[issue.req_id] = {
      missing_fields: issue.missing_fields || [],
      invalid_fields: issue.invalid_fields || [],
      severity: issue.severity,
      rule_type: issue.rule_type
    };
  }
  return index;
}

function getTopViolationPatterns(schemaIssues, topN = 5) {
  const fieldCounts = {};
  
  for (const issue of schemaIssues) {
    const ruleType = issue.rule_type;
    for (const field of issue.missing_fields || []) {
      const key = `${field}|missing|${ruleType}`;
      fieldCounts[key] = (fieldCounts[key] || 0) + 1;
    }
    for (const field of issue.invalid_fields || []) {
      const key = `${field}|invalid|${ruleType}`;
      fieldCounts[key] = (fieldCounts[key] || 0) + 1;
    }
  }
  
  const patterns = Object.entries(fieldCounts)
    .map(([key, count]) => {
      const [field, issueType, ruleType] = key.split('|');
      return { field, issueType, ruleType, count };
    })
    .sort((a, b) => b.count - a.count)
    .slice(0, topN);
  
  return patterns;
}

function getComplianceStatusCounts(requirements, schemaIndex) {
  let compliant = 0;
  let missingOnly = 0;
  let enumViolations = 0;
  let repairAttempted = 0;
  
  for (const req of requirements) {
    const issue = schemaIndex[req.requirement_id];
    if (!issue) {
      compliant++;
    } else if (issue.invalid_fields.length > 0) {
      enumViolations++;
    } else if (issue.missing_fields.length > 0) {
      missingOnly++;
    }
    
    if (req.attributes?._schema_validation?.repair_attempted) {
      repairAttempted++;
    }
  }
  
  return { compliant, missingOnly, enumViolations, repairAttempted, total: requirements.length };
}

function applyFilters(requirements, filters, hallucinationIndex, schemaIndex) {
  return requirements.filter(req => {
    if (filters.ruleType !== 'All' && req.rule_type !== filters.ruleType) return false;
    
    const halluc = hallucinationIndex[req.requirement_id];
    if (filters.hallucinationRisk !== 'All') {
      if (filters.hallucinationRisk === 'None' && halluc) return false;
      if (filters.hallucinationRisk !== 'None' && halluc?.risk !== filters.hallucinationRisk.toLowerCase()) return false;
    }
    
    const schema = schemaIndex[req.requirement_id];
    if (filters.schemaStatus !== 'All') {
      if (filters.schemaStatus === 'Compliant' && schema) return false;
      if (filters.schemaStatus === 'Has Issues' && !schema) return false;
    }
    
    if (req.confidence < filters.minConfidence) return false;
    
    if (filters.search && !req.rule_description.toLowerCase().includes(filters.search.toLowerCase())) return false;
    
    return true;
  });
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

function GateBadge({ decision, score, threshold }) {
  const isAccepted = decision === 'accept';
  return (
    <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-white font-medium ${isAccepted ? 'bg-accent-green' : 'bg-accent-red'}`}>
      {isAccepted ? <CheckCircle size={18} /> : <XCircle size={18} />}
      <span className="uppercase tracking-wide text-sm">
        {isAccepted ? 'ACCEPTED' : 'REJECTED'}
      </span>
      <span className="font-mono text-sm opacity-90">
        {score.toFixed(3)} / {threshold.toFixed(3)}
      </span>
    </div>
  );
}

function KPITile({ label, value, color, delay }) {
  const colorClasses = {
    blue: 'border-accent-blue text-accent-blue',
    green: 'border-accent-green text-accent-green',
    amber: 'border-accent-amber text-accent-amber',
    red: 'border-accent-red text-accent-red',
    neutral: 'border-text-muted text-text-primary'
  };
  
  return (
    <div 
      className={`bg-surface border border-border rounded-lg p-4 opacity-0 animate-fade-in animate-delay-${delay}`}
      style={{ animationFillMode: 'forwards' }}
    >
      <div className="text-xs uppercase tracking-wider text-text-muted mb-2">{label}</div>
      <div className={`text-3xl font-mono font-semibold ${colorClasses[color]}`}>
        {typeof value === 'number' ? (value < 1 && value > 0 ? value.toFixed(3) : value) : value}
      </div>
      <div className={`h-0.5 mt-3 rounded ${colorClasses[color].split(' ')[0].replace('border-', 'bg-')}`} />
    </div>
  );
}

function RuleTypeBar({ distribution, onSegmentClick, activeFilter }) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
  const data = Object.entries(distribution).map(([type, count]) => ({
    type,
    count,
    percentage: (count / total * 100).toFixed(1)
  }));
  
  return (
    <div className="bg-surface border border-border rounded-lg p-4 mt-4">
      <div className="text-xs uppercase tracking-wider text-text-muted mb-3">Rule Type Distribution</div>
      <div className="flex h-8 rounded overflow-hidden">
        {data.map(({ type, count, percentage }) => (
          <div
            key={type}
            className={`flex items-center justify-center cursor-pointer transition-opacity hover:opacity-80 ${activeFilter === type ? 'ring-2 ring-white ring-inset' : ''}`}
            style={{ 
              width: `${percentage}%`, 
              backgroundColor: RULE_TYPE_COLORS[type],
              minWidth: count > 0 ? '40px' : '0'
            }}
            onClick={() => onSegmentClick(type)}
            title={`${RULE_TYPE_LABELS[type]}: ${count}`}
          >
            <span className="text-xs font-mono text-white font-medium truncate px-1">
              {count}
            </span>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-3 mt-3">
        {data.map(({ type, count }) => (
          <div key={type} className="flex items-center gap-1.5 text-xs">
            <div className="w-2.5 h-2.5 rounded" style={{ backgroundColor: RULE_TYPE_COLORS[type] }} />
            <span className="text-text-muted">{RULE_TYPE_LABELS[type]}</span>
            <span className="font-mono text-text-primary">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CompliancePanel({ counts }) {
  const { compliant, missingOnly, enumViolations, repairAttempted, total } = counts;
  
  const bars = [
    { label: 'Fully Compliant', count: compliant, color: 'bg-accent-green', pct: (compliant / total * 100).toFixed(1) },
    { label: 'Missing Fields Only', count: missingOnly, color: 'bg-accent-amber', pct: (missingOnly / total * 100).toFixed(1) },
    { label: 'Enum Violations', count: enumViolations, color: 'bg-accent-red', pct: (enumViolations / total * 100).toFixed(1) }
  ];
  
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="text-xs uppercase tracking-wider text-text-muted mb-4">Compliance Status</div>
      <div className="space-y-3">
        {bars.map(({ label, count, color, pct }) => (
          <div key={label}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-text-muted">{label}</span>
              <span className="font-mono text-text-primary">{count} ({pct}%)</span>
            </div>
            <div className="h-2 bg-border rounded overflow-hidden">
              <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-3 border-t border-border text-sm text-text-muted">
        Repair attempted on <span className="font-mono text-text-primary">{repairAttempted}</span> requirements
      </div>
    </div>
  );
}

function ViolationPatternsTable({ patterns }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="text-xs uppercase tracking-wider text-text-muted mb-4">Top Violation Patterns</div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-text-muted text-xs uppercase tracking-wider">
            <th className="text-left pb-2">Field / Issue</th>
            <th className="text-left pb-2">Rule Type</th>
            <th className="text-right pb-2">Count</th>
            <th className="text-right pb-2">Severity</th>
          </tr>
        </thead>
        <tbody>
          {patterns.map((p, i) => (
            <tr key={i} className="border-t border-border">
              <td className="py-2">
                <span className="font-mono text-text-primary">{p.field.split(':')[0]}</span>
                <span className="text-text-muted ml-2">{p.issueType}</span>
              </td>
              <td className="py-2">
                <span 
                  className="px-2 py-0.5 rounded text-xs font-medium"
                  style={{ backgroundColor: RULE_TYPE_COLORS[p.ruleType] + '30', color: RULE_TYPE_COLORS[p.ruleType] }}
                >
                  {RULE_TYPE_LABELS[p.ruleType]}
                </span>
              </td>
              <td className="py-2 text-right font-mono">{p.count}</td>
              <td className="py-2 text-right">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${p.count > 30 ? 'bg-accent-red/20 text-accent-red' : 'bg-accent-amber/20 text-accent-amber'}`}>
                  {p.count > 30 ? 'High' : 'Medium'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ConfidenceBar({ value, showValue = true }) {
  const color = value >= 0.80 ? 'bg-accent-green' : value >= 0.65 ? 'bg-accent-amber' : 'bg-accent-red';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-border rounded overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${value * 100}%` }} />
      </div>
      {showValue && <span className="font-mono text-xs w-10 text-right">{value.toFixed(2)}</span>}
    </div>
  );
}

function SubScoreBar({ label, value, maxScale = 0.35, isLowest = false }) {
  const pct = Math.min((value / maxScale) * 100, 100);
  const barColor = isLowest ? 'bg-accent-red' : value === 0 ? 'bg-accent-red/50' : 'bg-accent-blue';
  
  return (
    <div className="flex items-center gap-3">
      <div className="w-32 text-xs text-text-muted truncate">{label}</div>
      <div className="flex-1 h-3 bg-border rounded overflow-hidden">
        <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <div className={`font-mono text-xs w-12 text-right ${value === 0 ? 'text-accent-red' : ''}`}>
        {value.toFixed(3)}
        {value === 0 && <span className="ml-1 text-accent-red">!</span>}
      </div>
    </div>
  );
}

function RequirementAccordion({ req, schemaIssue, isOpen, onToggle }) {
  const features = req.attributes?._confidence_features || {};
  const grounding = req.attributes?._grounding_evidence || {};
  const applicableFields = req.attributes?.applicable_fields || [];
  const schemaValidation = req.attributes?._schema_validation || {};
  
  const subScores = [
    { label: 'Grounding Match', value: features.grounding_match || 0 },
    { label: 'Completeness', value: features.completeness || 0 },
    { label: 'Quantification', value: features.quantification || 0 },
    { label: 'Schema Compliance', value: features.schema_compliance || 0 },
    { label: 'Coherence', value: features.coherence || 0 },
    { label: 'Domain Signals', value: features.domain_signals || 0 }
  ];
  
  const lowestIdx = subScores.reduce((minIdx, s, idx, arr) => s.value < arr[minIdx].value ? idx : minIdx, 0);
  
  return (
    <div className={`accordion-content ${isOpen ? 'expanded' : 'collapsed'}`}>
      <div className="bg-background border-t border-border p-4 space-y-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">Rule Description</div>
          <div className="text-sm text-text-primary">{req.rule_description}</div>
        </div>
        
        <div>
          <div className="text-xs uppercase tracking-wider text-text-muted mb-1">
            Grounded In
            {grounding.jaccard_score && (
              <span className="ml-2 font-mono text-accent-blue">
                Jaccard: {grounding.jaccard_score?.toFixed(3)} | Phrases: {grounding.phrase_count || 0}
              </span>
            )}
          </div>
          <div className="text-sm text-text-muted italic">{req.grounded_in}</div>
        </div>
        
        <div>
          <div className="text-xs uppercase tracking-wider text-text-muted mb-2">
            Confidence Breakdown
            <span className="ml-2 font-mono text-text-primary">Total: {req.confidence.toFixed(2)}</span>
          </div>
          <div className="space-y-1.5">
            {subScores.map((s, i) => (
              <SubScoreBar key={s.label} label={s.label} value={s.value} isLowest={i === lowestIdx} />
            ))}
          </div>
        </div>
        
        {schemaIssue && (
          <div>
            <div className="text-xs uppercase tracking-wider text-text-muted mb-2">Schema Issues</div>
            <div className="space-y-1 text-sm">
              {schemaIssue.missing_fields.length > 0 && (
                <div className="flex items-start gap-2">
                  <X size={14} className="text-accent-red mt-0.5" />
                  <span className="text-text-muted">Missing: </span>
                  <span className="font-mono text-accent-red">{schemaIssue.missing_fields.join(' · ')}</span>
                </div>
              )}
              {schemaIssue.invalid_fields.length > 0 && (
                <div className="flex items-start gap-2">
                  <X size={14} className="text-accent-red mt-0.5" />
                  <span className="text-text-muted">Invalid: </span>
                  <span className="font-mono text-accent-red">{schemaIssue.invalid_fields.join(' · ')}</span>
                </div>
              )}
              <div className="flex items-center gap-2 text-text-muted">
                <span>Repair attempted:</span>
                <span className={`font-mono ${schemaValidation.repair_attempted ? 'text-accent-amber' : 'text-text-muted'}`}>
                  {schemaValidation.repair_attempted ? 'YES' : 'NO'}
                </span>
              </div>
            </div>
          </div>
        )}
        
        {applicableFields.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wider text-text-muted mb-1">Applicable Fields</div>
            <div className="text-sm font-mono text-accent-blue">
              {applicableFields.slice(0, 3).join(' · ')}
              {applicableFields.length > 3 && <span className="text-text-muted"> +{applicableFields.length - 3} more</span>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function RequirementsTable({ requirements, hallucinationIndex, schemaIndex, filters, setFilters }) {
  const [expandedId, setExpandedId] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [page, setPage] = useState(0);
  const pageSize = 25;
  
  const filteredReqs = useMemo(() => 
    applyFilters(requirements, filters, hallucinationIndex, schemaIndex),
    [requirements, filters, hallucinationIndex, schemaIndex]
  );
  
  const sortedReqs = useMemo(() => {
    if (!sortConfig.key) return filteredReqs;
    return [...filteredReqs].sort((a, b) => {
      let aVal = sortConfig.key === 'confidence' ? a.confidence : a.requirement_id;
      let bVal = sortConfig.key === 'confidence' ? b.confidence : b.requirement_id;
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredReqs, sortConfig]);
  
  const paginatedReqs = sortedReqs.slice(page * pageSize, (page + 1) * pageSize);
  const totalPages = Math.ceil(sortedReqs.length / pageSize);
  
  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };
  
  const ruleTypes = ['All', ...new Set(requirements.map(r => r.rule_type))];
  const activeFilterCount = Object.entries(filters).filter(([k, v]) => {
    if (k === 'minConfidence') return v > 0.50;
    if (k === 'search') return v !== '';
    return v !== 'All';
  }).length;
  
  return (
    <div>
      {/* Filter Bar */}
      <div className="bg-surface border border-border rounded-lg p-4 mb-4 sticky top-16 z-10">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-text-muted" />
            <span className="text-xs uppercase tracking-wider text-text-muted">Filters</span>
          </div>
          
          <select 
            className="bg-background border border-border rounded px-3 py-1.5 text-sm text-text-primary"
            value={filters.ruleType}
            onChange={e => setFilters(f => ({ ...f, ruleType: e.target.value }))}
          >
            {ruleTypes.map(t => (
              <option key={t} value={t}>{t === 'All' ? 'All Rule Types' : RULE_TYPE_LABELS[t] || t}</option>
            ))}
          </select>
          
          <select 
            className="bg-background border border-border rounded px-3 py-1.5 text-sm text-text-primary"
            value={filters.hallucinationRisk}
            onChange={e => setFilters(f => ({ ...f, hallucinationRisk: e.target.value }))}
          >
            <option value="All">All Halluc. Risk</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="None">None</option>
          </select>
          
          <select 
            className="bg-background border border-border rounded px-3 py-1.5 text-sm text-text-primary"
            value={filters.schemaStatus}
            onChange={e => setFilters(f => ({ ...f, schemaStatus: e.target.value }))}
          >
            <option value="All">All Schema Status</option>
            <option value="Compliant">Compliant</option>
            <option value="Has Issues">Has Issues</option>
          </select>
          
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">Min Conf:</span>
            <input 
              type="range" 
              min="0.50" 
              max="0.89" 
              step="0.01"
              value={filters.minConfidence}
              onChange={e => setFilters(f => ({ ...f, minConfidence: parseFloat(e.target.value) }))}
              className="w-24"
            />
            <span className="font-mono text-xs text-text-primary w-10">{filters.minConfidence.toFixed(2)}</span>
          </div>
          
          <input 
            type="text"
            placeholder="Search descriptions..."
            className="bg-background border border-border rounded px-3 py-1.5 text-sm text-text-primary flex-1 min-w-48"
            value={filters.search}
            onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
          />
          
          {activeFilterCount > 0 && (
            <button 
              className="flex items-center gap-1 px-3 py-1.5 bg-accent-blue/20 text-accent-blue rounded text-sm hover:bg-accent-blue/30"
              onClick={() => setFilters({ ruleType: 'All', hallucinationRisk: 'All', schemaStatus: 'All', minConfidence: 0.50, search: '' })}
            >
              <X size={14} />
              Clear ({activeFilterCount})
            </button>
          )}
        </div>
        <div className="mt-2 text-xs text-text-muted">
          Showing {paginatedReqs.length} of {sortedReqs.length} requirements
        </div>
      </div>
      
      {/* Table */}
      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-text-muted text-xs uppercase tracking-wider bg-background">
              <th className="text-left p-3 cursor-pointer hover:text-text-primary" onClick={() => handleSort('requirement_id')}>
                Req ID {sortConfig.key === 'requirement_id' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
              </th>
              <th className="text-left p-3">Rule Type</th>
              <th className="text-left p-3 cursor-pointer hover:text-text-primary" onClick={() => handleSort('confidence')}>
                Confidence {sortConfig.key === 'confidence' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
              </th>
              <th className="text-left p-3">Grounding</th>
              <th className="text-left p-3">Halluc. Risk</th>
              <th className="text-left p-3">Schema</th>
            </tr>
          </thead>
          <tbody>
            {paginatedReqs.map((req, idx) => {
              const halluc = hallucinationIndex[req.requirement_id];
              const schema = schemaIndex[req.requirement_id];
              const grounding = req.attributes?._grounding_classification || '—';
              const isExpanded = expandedId === req.requirement_id;
              
              return (
                <React.Fragment key={req.requirement_id}>
                  <tr 
                    className={`border-t border-border cursor-pointer transition-all hover:bg-background ${idx % 2 === 0 ? 'bg-surface' : 'bg-surface/50'} ${isExpanded ? 'border-l-4 border-l-accent-blue' : 'hover:border-l-4 hover:border-l-accent-blue/50'}`}
                    onClick={() => setExpandedId(isExpanded ? null : req.requirement_id)}
                  >
                    <td className="p-3 font-mono text-text-muted text-xs">{req.requirement_id}</td>
                    <td className="p-3">
                      <span 
                        className="px-2 py-0.5 rounded text-xs font-medium"
                        style={{ backgroundColor: RULE_TYPE_COLORS[req.rule_type] + '30', color: RULE_TYPE_COLORS[req.rule_type] }}
                      >
                        {RULE_TYPE_LABELS[req.rule_type] || req.rule_type}
                      </span>
                    </td>
                    <td className="p-3 w-40">
                      <ConfidenceBar value={req.confidence} />
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${grounding === 'EXACT' ? 'bg-accent-green/20 text-accent-green' : grounding === 'INFERENCE' ? 'bg-accent-red/20 text-accent-red' : 'bg-accent-amber/20 text-accent-amber'}`}>
                        {grounding}
                      </span>
                    </td>
                    <td className="p-3">
                      {halluc ? (
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${halluc.risk === 'critical' ? 'bg-accent-red/20 text-accent-red' : halluc.risk === 'high' ? 'bg-accent-amber/20 text-accent-amber' : 'bg-accent-blue/20 text-accent-blue'}`}>
                          {halluc.risk === 'critical' ? '● Critical' : halluc.risk === 'high' ? '● High' : '● Medium'}
                        </span>
                      ) : (
                        <span className="text-text-muted">—</span>
                      )}
                    </td>
                    <td className="p-3">
                      {schema ? (
                        <span className="text-accent-amber text-xs">
                          <AlertTriangle size={12} className="inline mr-1" />
                          {schema.missing_fields.length + schema.invalid_fields.length} issues
                        </span>
                      ) : (
                        <span className="text-accent-green text-xs">
                          <CheckCircle size={12} className="inline mr-1" />
                          Compliant
                        </span>
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td colSpan={6} className="p-0">
                      <RequirementAccordion 
                        req={req} 
                        schemaIssue={schema} 
                        isOpen={isExpanded}
                        onToggle={() => setExpandedId(isExpanded ? null : req.requirement_id)}
                      />
                    </td>
                  </tr>
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
        
        {/* Pagination */}
        <div className="flex items-center justify-between p-3 border-t border-border bg-background">
          <div className="text-xs text-text-muted">
            Page {page + 1} of {totalPages}
          </div>
          <div className="flex gap-2">
            <button 
              className="px-3 py-1 bg-surface border border-border rounded text-sm disabled:opacity-50"
              disabled={page === 0}
              onClick={() => setPage(p => p - 1)}
            >
              Previous
            </button>
            <button 
              className="px-3 py-1 bg-surface border border-border rounded text-sm disabled:opacity-50"
              disabled={page >= totalPages - 1}
              onClick={() => setPage(p => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN DASHBOARD
// ============================================================================

export default function Dashboard() {
  const { requirements, extraction_metadata, eval_report, gate_decision } = rawData;
  
  const hallucinationIndex = useMemo(() => buildHallucinationIndex(eval_report), [eval_report]);
  const schemaIndex = useMemo(() => buildSchemaIndex(eval_report), [eval_report]);
  const complianceCounts = useMemo(() => getComplianceStatusCounts(requirements, schemaIndex), [requirements, schemaIndex]);
  const violationPatterns = useMemo(() => getTopViolationPatterns(eval_report?.schema_compliance_issues || []), [eval_report]);
  
  const [filters, setFilters] = useState({
    ruleType: 'All',
    hallucinationRisk: 'All',
    schemaStatus: 'All',
    minConfidence: 0.50,
    search: ''
  });
  
  const handleRuleTypeClick = (type) => {
    setFilters(f => ({ ...f, ruleType: f.ruleType === type ? 'All' : type }));
  };
  
  const avgConfColor = extraction_metadata.avg_confidence < 0.65 ? 'red' : extraction_metadata.avg_confidence < 0.80 ? 'amber' : 'green';
  const qualityColor = eval_report.overall_quality_score < 0.40 ? 'red' : eval_report.overall_quality_score < 0.70 ? 'amber' : 'green';
  
  return (
    <div className="min-h-screen bg-background">
      {/* Fixed Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-background/95 backdrop-blur border-b border-border">
        <div className="max-w-[1400px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4 text-sm">
            <span className="font-semibold text-text-primary">FDIC Part 370 · IT Controls Extraction</span>
            <span className="text-text-muted font-mono">Model: claude-sonnet-4</span>
            <span className="text-text-muted font-mono">Prompt: v1.0</span>
            <span className="text-text-muted font-mono">Run: 2026-02-22</span>
          </div>
          <GateBadge 
            decision={gate_decision.decision} 
            score={gate_decision.score} 
            threshold={gate_decision.thresholds_applied.auto_accept} 
          />
        </div>
      </header>
      
      {/* Main Content */}
      <main className="max-w-[1400px] mx-auto px-6 pt-20 pb-12">
        {/* Section: KPI Tiles */}
        <section className="mb-8">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-4 border-b border-border pb-2">
            Extraction Command Center
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <KPITile label="Requirements Extracted" value={extraction_metadata.total_requirements_extracted} color="blue" delay={0} />
            <KPITile label="Avg Confidence" value={extraction_metadata.avg_confidence} color={avgConfColor} delay={1} />
            <KPITile label="Chunks Processed" value={extraction_metadata.total_chunks_processed} color="neutral" delay={2} />
            <KPITile label="Hallucination Flags" value={eval_report.hallucination_flags?.length || 0} color="red" delay={3} />
            <KPITile label="Overall Quality Score" value={eval_report.overall_quality_score} color={qualityColor} delay={4} />
          </div>
          <RuleTypeBar 
            distribution={extraction_metadata.rule_type_distribution} 
            onSegmentClick={handleRuleTypeClick}
            activeFilter={filters.ruleType !== 'All' ? filters.ruleType : null}
          />
        </section>
        
        {/* Section: Schema Compliance */}
        <section className="mb-8">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-4 border-b border-border pb-2">
            Schema Compliance Breakdown
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <CompliancePanel counts={complianceCounts} />
            <ViolationPatternsTable patterns={violationPatterns} />
          </div>
        </section>
        
        {/* Section: Requirements Table */}
        <section className="mb-8">
          <div className="text-xs uppercase tracking-wider text-text-muted mb-4 border-b border-border pb-2">
            Requirements Registry
          </div>
          <RequirementsTable 
            requirements={requirements}
            hallucinationIndex={hallucinationIndex}
            schemaIndex={schemaIndex}
            filters={filters}
            setFilters={setFilters}
          />
        </section>
      </main>
      
      {/* Footer */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-[1400px] mx-auto px-6 py-4 flex items-center justify-between text-xs">
          <div className="font-mono text-text-muted">
            Extracted: 2026-02-22 · LLM Calls: {extraction_metadata.total_llm_calls || 24} · Model: claude-sonnet-4 · Prompt: v1.0 · Iteration: {extraction_metadata.extraction_iteration || 1}
          </div>
          <div className="flex items-center gap-2 text-accent-amber">
            <AlertTriangle size={14} />
            <span>AI-extracted output. Human review required for all requirements flagged Critical or classified INFERENCE.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
