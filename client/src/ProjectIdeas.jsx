import { useMemo, useState } from 'react'

const ideas = [
  {
    branch: 'CSE', level: 'beginner', title: 'Campus Lost & Found Board',
    description: 'Create a simple campus page where students can post misplaced items and mark them as reunited.',
    skills: ['HTML and CSS', 'JavaScript', 'Form validation'],
    features: ['Search by item or location', 'Lost and found filters', 'Responsive listing cards'],
    effort: '1–2 weekends'
  },
  {
    branch: 'CSE', level: 'intermediate', title: 'Study Group Matchmaker',
    description: 'Build a small tool that pairs students by subject, preferred study time and learning goals.',
    skills: ['React', 'Filtering and sorting', 'UI design'],
    features: ['Subject-based discovery', 'Time availability', 'Group size preferences'],
    effort: '2–4 weeks'
  },
  {
    branch: 'CSE', level: 'advanced', title: 'Smart Lab Equipment Tracker',
    description: 'Prototype a dashboard for reserving shared lab equipment and flagging maintenance needs.',
    skills: ['Full-stack development', 'Database design', 'Access control'],
    features: ['Equipment availability', 'Booking calendar', 'Maintenance queue'],
    effort: '4–8 weeks'
  },
  {
    branch: 'ME', level: 'beginner', title: 'Workshop Safety Checklist',
    description: 'Design a clear pre-workshop checklist that helps classmates remember protective equipment and setup steps.',
    skills: ['Technical documentation', 'UI design', 'Basic web forms'],
    features: ['Workshop-specific lists', 'Completion progress', 'Printable checklist'],
    effort: '1 weekend'
  },
  {
    branch: 'ME', level: 'intermediate', title: 'Gear Ratio Explorer',
    description: 'Make an interactive calculator that explains how input and output gear sizes affect speed and torque.',
    skills: ['Mechanical fundamentals', 'JavaScript', 'Data visualisation'],
    features: ['Gear configuration', 'Speed and torque estimates', 'Annotated diagram'],
    effort: '2–3 weeks'
  },
  {
    branch: 'ME', level: 'advanced', title: 'Desktop CNC Job Estimator',
    description: 'Prototype a planner that estimates machining time from safe, user-entered feed and path measurements.',
    skills: ['Manufacturing processes', 'Geometry', 'Application design'],
    features: ['Tool parameter inputs', 'Path length estimate', 'Setup-time breakdown'],
    effort: '4–6 weeks'
  },
  {
    branch: 'EE', level: 'beginner', title: 'Ohm’s Law Learning Cards',
    description: 'Create a visual set of short circuit questions that reveal the voltage, current and resistance relationship.',
    skills: ['Circuit fundamentals', 'JavaScript', 'Instructional design'],
    features: ['Randomised practice', 'Step-by-step hints', 'Instant answer checks'],
    effort: '1–2 weekends'
  },
  {
    branch: 'EE', level: 'intermediate', title: 'Household Energy Planner',
    description: 'Build an estimate tool that compares appliance usage scenarios and helps students understand energy units.',
    skills: ['Power systems basics', 'Data handling', 'Interface design'],
    features: ['Appliance list', 'Daily and monthly estimates', 'Scenario comparison'],
    effort: '2–3 weeks'
  },
  {
    branch: 'EE', level: 'advanced', title: 'Renewable Microgrid Monitor',
    description: 'Prototype a small dashboard that visualises sample solar generation, storage and demand data.',
    skills: ['Power electronics', 'Data visualisation', 'Embedded systems'],
    features: ['Generation and demand chart', 'Battery state display', 'Peak-use alerts'],
    effort: '5–8 weeks'
  },
  {
    branch: 'ECE', level: 'beginner', title: 'Digital Logic Truth Table Lab',
    description: 'Let learners combine basic logic gates and see the resulting truth table update immediately.',
    skills: ['Boolean algebra', 'JavaScript', 'Learning experience design'],
    features: ['AND, OR and NOT gates', 'Live truth tables', 'Practice questions'],
    effort: '1–2 weekends'
  },
  {
    branch: 'ECE', level: 'intermediate', title: 'Sensor Signal Visualiser',
    description: 'Display sample readings from a simulated sensor and explain how noise changes a signal.',
    skills: ['Signal fundamentals', 'Charting', 'Embedded C concepts'],
    features: ['Adjustable sampling rate', 'Noise level control', 'Raw vs filtered signal'],
    effort: '2–4 weeks'
  },
  {
    branch: 'ECE', level: 'advanced', title: 'Low-Cost Smart Greenhouse',
    description: 'Plan an embedded prototype that monitors environmental readings and controls a small demonstration setup.',
    skills: ['Microcontrollers', 'Sensors', 'IoT security basics'],
    features: ['Temperature and humidity sensing', 'Threshold-based control', 'Offline status indicator'],
    effort: '5–8 weeks'
  },
  {
    branch: 'CE', level: 'beginner', title: 'Material Quantity Quick Check',
    description: 'Build a simple estimator for common classroom examples of area, volume and material quantities.',
    skills: ['Measurement', 'Civil engineering basics', 'JavaScript'],
    features: ['Shape-based input', 'Unit labels', 'Worked example'],
    effort: '1–2 weekends'
  },
  {
    branch: 'CE', level: 'intermediate', title: 'Rainwater Harvesting Planner',
    description: 'Estimate rooftop collection potential from sample rainfall and roof measurements for an academic project.',
    skills: ['Water resources', 'Unit conversion', 'Data visualisation'],
    features: ['Rainfall and roof inputs', 'Monthly estimate chart', 'Storage-size comparison'],
    effort: '2–4 weeks'
  },
  {
    branch: 'CE', level: 'advanced', title: 'Accessible Campus Route Map',
    description: 'Prototype a campus map that highlights step-free paths, ramps and construction notices.',
    skills: ['Surveying', 'Mapping', 'Accessibility research'],
    features: ['Accessible path options', 'Obstacle reports', 'Building entrance details'],
    effort: '5–8 weeks'
  },
  {
    branch: 'MLT', level: 'beginner', title: 'Specimen Label Practice',
    description: 'Create a training exercise for checking specimen labels against sample collection details.',
    skills: ['Lab workflow basics', 'Form design', 'Quality assurance'],
    features: ['Sample scenarios', 'Label-check checklist', 'Immediate feedback'],
    effort: '1–2 weekends'
  },
  {
    branch: 'MLT', level: 'intermediate', title: 'Dilution Practice Lab',
    description: 'Build a guided practice tool for dilution calculations with clear units and worked examples.',
    skills: ['Concentration calculations', 'Unit conversion', 'JavaScript'],
    features: ['C₁V₁ = C₂V₂ problems', 'Hint steps', 'Answer validation'],
    effort: '2–3 weeks'
  },
  {
    branch: 'MLT', level: 'advanced', title: 'Laboratory Quality Dashboard',
    description: 'Prototype a dashboard that uses sample data to explain quality-control trends and out-of-range results.',
    skills: ['Quality control', 'Chart interpretation', 'Laboratory safety'],
    features: ['Sample control charts', 'Flagged trends', 'Plain-language interpretation'],
    effort: '4–6 weeks'
  }
]

const levels = ['beginner', 'intermediate', 'advanced']

export default function ProjectIdeas() {
  const [branch, setBranch] = useState('CSE')
  const [level, setLevel] = useState('beginner')
  const [ideaIndex, setIdeaIndex] = useState(0)
  const filteredIdeas = useMemo(
    () => ideas.filter(idea => idea.branch === branch && idea.level === level),
    [branch, level]
  )
  const idea = filteredIdeas[ideaIndex % Math.max(filteredIdeas.length, 1)]

  const choose = (setter, value) => {
    setter(value)
    setIdeaIndex(0)
  }

  const nextIdea = () => {
    if (filteredIdeas.length > 1) {
      setIdeaIndex(index => {
        const offset = 1 + Math.floor(Math.random() * (filteredIdeas.length - 1))
        return (index + offset) % filteredIdeas.length
      })
    }
  }

  return <div className="idea-generator">
    <div className="idea-controls">
      <label>Branch
        <select value={branch} onChange={event => choose(setBranch, event.target.value)}>
          {['CSE', 'ME', 'EE', 'ECE', 'CE', 'MLT'].map(code => <option key={code} value={code}>{code}</option>)}
        </select>
      </label>
      <label>Project difficulty
        <select value={level} onChange={event => choose(setLevel, event.target.value)}>
          {levels.map(item => <option value={item} key={item}>{item[0].toUpperCase() + item.slice(1)}</option>)}
        </select>
      </label>
      <button className="btn primary" onClick={nextIdea}>Surprise me <span aria-hidden="true">↗</span></button>
    </div>
    {idea&&<article className="idea-card">
      <div className="idea-card-top"><span className="tag">{idea.branch} · {idea.level}</span><span>{idea.effort}</span></div>
      <h2>{idea.title}</h2>
      <p>{idea.description}</p>
      <div className="idea-details">
        <div><h3>Skills to explore</h3><ul>{idea.skills.map(skill=><li key={skill}>{skill}</li>)}</ul></div>
        <div><h3>Possible features</h3><ul>{idea.features.map(feature=><li key={feature}>{feature}</li>)}</ul></div>
      </div>
      <p className="idea-footnote">Starting point only—shape the scope with your teammates and keep safety in mind for physical prototypes.</p>
    </article>}
  </div>
}
