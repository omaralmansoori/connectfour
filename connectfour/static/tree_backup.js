// Tree visualization for Connect Four AI diagnostics
class TreeVisualizer {
  constructor(treeData, principalVariation) {
    this.treeData = treeData;
    this.principalVariation = principalVariation || [];
    this.container = document.getElementById('treeContainer');
    this.showScores = true;
    this.highlightBest = true;
    this.showBestOnly = true;
    
    this.nodeWidth = 160;
    this.nodeHeight = 70;
    this.levelHeight = 120;
    this.nodeSpacing = 20;
    
    this.setupControls();
    this.render();
  }
  
  setupControls() {
    const showScoresCheckbox = document.getElementById('showScores');
    const highlightBestCheckbox = document.getElementById('highlightBest');
    const showBestOnlyCheckbox = document.getElementById('showBestOnly');
    
    if (showScoresCheckbox) {
      showScoresCheckbox.addEventListener('change', (e) => {
        this.showScores = e.target.checked;
        this.render();
      });
    }
    
    if (highlightBestCheckbox) {
      highlightBestCheckbox.addEventListener('change', (e) => {
        this.highlightBest = e.target.checked;
        this.render();
      });
    }
    
    if (showBestOnlyCheckbox) {
      showBestOnlyCheckbox.addEventListener('change', (e) => {
        this.showBestOnly = e.target.checked;
        this.render();
      });
    }
  }
  
  isInPrincipalVariation(node, depth) {
    if (!this.highlightBest || !this.principalVariation || this.principalVariation.length === 0) {
      return false;
    }
    
    // Check if this node's column matches the expected move at this depth
    if (depth < this.principalVariation.length) {
      return node.column === this.principalVariation[depth];
    }
    return false;
  }
  
  calculateNodePositions(node, depth = 0, offset = 0) {
    const positions = [];
    
    if (!node || !node.children || node.children.length === 0) {
      return positions;
    }
    
    // Filter children based on showBestOnly setting
    let childrenToShow = node.children;
    if (this.showBestOnly && this.principalVariation && this.principalVariation.length > 0) {
      // Only show the child that's in the principal variation at this depth
      if (depth < this.principalVariation.length) {
        const bestColumn = this.principalVariation[depth];
        childrenToShow = node.children.filter(child => child.column === bestColumn);
      }
    }
    
    // Calculate total width needed for this subtree
    const childrenWithPositions = childrenToShow.map((child, index) => {
      const childPositions = this.calculateNodePositions(child, depth + 1, offset);
      return { child, positions: childPositions };
    });
    
    // Calculate x positions for children
    let currentX = offset;
    const childPositionData = [];
    
    childrenWithPositions.forEach(({ child, positions: childPositions }) => {
      const childWidth = Math.max(
        this.nodeWidth,
        childPositions.length > 0 
          ? Math.max(...childPositions.map(p => p.x)) - Math.min(...childPositions.map(p => p.x)) + this.nodeWidth
          : this.nodeWidth
      );
      
      const childX = currentX + childWidth / 2 - this.nodeWidth / 2;
      
      childPositionData.push({
        child,
        x: childX,
        y: depth * this.levelHeight,
        positions: childPositions
      });
      
      currentX += childWidth + this.nodeSpacing;
    });
    
    // Add all child positions
    childPositionData.forEach(({ child, x, y, positions: childPositions }) => {
      const isInPV = this.isInPrincipalVariation(child, depth);
      
      positions.push({
        node: child,
        x,
        y,
        depth,
        isInPV
      });
      
      positions.push(...childPositions);
    });
    
    return positions;
  }
  
  render() {
    // Clear container
    this.container.innerHTML = '';
    
    if (!this.treeData || !this.treeData.children || this.treeData.children.length === 0) {
      this.container.innerHTML = '<p style="color: var(--muted); padding: 20px;">No tree data available</p>';
      return;
    }
    
    // Calculate positions for all nodes
    const positions = this.calculateNodePositions(this.treeData);
    
    if (positions.length === 0) {
      this.container.innerHTML = '<p style="color: var(--muted); padding: 20px;">No nodes to display</p>';
      return;
    }
    
    // Find bounds
    const minX = Math.min(...positions.map(p => p.x));
    const maxX = Math.max(...positions.map(p => p.x)) + this.nodeWidth;
    const maxY = Math.max(...positions.map(p => p.y)) + this.nodeHeight;
    
    // Create SVG for edges
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.style.position = 'absolute';
    svg.style.top = '0';
    svg.style.left = '0';
    svg.style.width = (maxX - minX + 40) + 'px';
    svg.style.height = (maxY + 40) + 'px';
    svg.style.pointerEvents = 'none';
    this.container.appendChild(svg);
    
    // Set container size
    this.container.style.position = 'relative';
    this.container.style.width = (maxX - minX + 40) + 'px';
    this.container.style.minHeight = (maxY + 40) + 'px';
    
    // Draw edges first (so they appear behind nodes)
    const positionMap = new Map();
    positions.forEach(p => {
      const key = `${p.node.depth}_${p.node.column}`;
      positionMap.set(key, p);
    });
    
    positions.forEach(pos => {
      if (pos.node.children && pos.node.children.length > 0) {
        pos.node.children.forEach(child => {
          const childKey = `${child.depth}_${child.column}`;
          const childPos = positionMap.get(childKey);
          
          if (childPos) {
            const isInPV = pos.isInPV && childPos.isInPV;
            this.drawEdge(
              svg,
              pos.x - minX + this.nodeWidth / 2 + 20,
              pos.y + this.nodeHeight + 20,
              childPos.x - minX + this.nodeWidth / 2 + 20,
              childPos.y + 20,
              isInPV
            );
          }
        });
      }
    });
    
    // Draw nodes
    positions.forEach(pos => {
      this.drawNode(
        pos.node,
        pos.x - minX + 20,
        pos.y + 20,
        pos.depth,
        pos.isInPV
      );
    });
  }
  
  drawEdge(svg, x1, y1, x2, y2, isInPV) {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', x1);
    line.setAttribute('y1', y1);
    line.setAttribute('x2', x2);
    line.setAttribute('y2', y2);
    line.setAttribute('class', isInPV ? 'best-path' : '');
    line.style.stroke = isInPV ? 'var(--accent)' : 'rgba(159, 177, 208, 0.3)';
    line.style.strokeWidth = isInPV ? '3' : '2';
    
    svg.appendChild(line);
  }
  
  drawNode(node, x, y, depth, isInPV) {
    const nodeEl = document.createElement('div');
    nodeEl.className = 'tree-node';
    
    // Determine if this is an AI or Human turn
    const isAITurn = node.maximizing;
    if (isAITurn) {
      nodeEl.classList.add('ai-turn');
    } else {
      nodeEl.classList.add('human-turn');
    }
    
    if (isInPV) {
      nodeEl.classList.add('best-path');
    }
    
    nodeEl.style.left = x + 'px';
    nodeEl.style.top = y + 'px';
    
    // Node content
    const label = document.createElement('span');
    label.className = 'node-label';
    label.textContent = depth === 0 ? 'Root' : `Column ${node.column}`;
    nodeEl.appendChild(label);
    
    const info = document.createElement('span');
    info.className = 'node-info';
    info.textContent = `Depth ${node.depth} • ${isAITurn ? 'AI' : 'Human'}`;
    nodeEl.appendChild(info);
    
    if (this.showScores) {
      const score = document.createElement('span');
      score.className = 'node-score';
      score.textContent = `Score: ${node.score}`;
      nodeEl.appendChild(score);
    }
    
    // Add tooltip on hover
    nodeEl.addEventListener('mouseenter', (e) => {
      this.showTooltip(e, node, isAITurn);
    });
    
    nodeEl.addEventListener('mouseleave', () => {
      this.hideTooltip();
    });
    
    this.container.appendChild(nodeEl);
  }
  
  showTooltip(event, node, isAITurn) {
    let tooltip = document.querySelector('.node-tooltip');
    if (!tooltip) {
      tooltip = document.createElement('div');
      tooltip.className = 'node-tooltip';
      document.body.appendChild(tooltip);
    }
    
    tooltip.innerHTML = `
      <div style="margin-bottom: 6px;"><strong>Node Details</strong></div>
      <div>Column: ${node.column !== undefined ? node.column : 'N/A'}</div>
      <div>Depth: ${node.depth}</div>
      <div>Score: ${node.score}</div>
      <div>Turn: ${isAITurn ? 'AI (Maximizing)' : 'Human (Minimizing)'}</div>
      <div>Children: ${node.children ? node.children.length : 0}</div>
    `;
    
    tooltip.classList.add('visible');
    
    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = (rect.right + 10) + 'px';
    tooltip.style.top = rect.top + 'px';
  }
  
  hideTooltip() {
    const tooltip = document.querySelector('.node-tooltip');
    if (tooltip) {
      tooltip.classList.remove('visible');
    }
  }
}

// Initialize tree when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  if (typeof treeData !== 'undefined' && typeof principalVariation !== 'undefined') {
    new TreeVisualizer(treeData, principalVariation);
  }
});
