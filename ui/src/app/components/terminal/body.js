//
//  body.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React, {useEffect, useRef} from 'react'

import { 
  Table,
  Feed
} from 'semantic-ui-react'

export default class TerminalBody extends React.Component {
  constructor(props) {
    super(props)

    this.renderLineItem = this.renderLineItem.bind(this)
    this.renderLines    = this.renderLines.bind(this)
  }

  scrollToBottom() {
    this.outputEnd.scrollIntoView({behavior: 'smooth'})
  }

  componentDidMount() {
    this.scrollToBottom()
  }

  componentDidUpdate() {
    this.scrollToBottom()
  }

  renderLineItem(item, index) {
    return (
      <Feed.Event key={index}>
        <Feed.Content>
          <Feed.Summary>
            {item.replace("echo:", "") || "No output"}
          </Feed.Summary>
        </Feed.Content>
      </Feed.Event>
    )
  }

  renderLines() {
    return (this.props.buffer || []).map((line, idx) => {
      return this.renderLineItem(line, `output-line-${idx}`)
    })
  }

  render() {
    return (
      <Feed style={{width: '100%', height: '100%', overflow: 'auto hidden'}}>
        {this.renderLines()}
        <Feed.Event><span ref={(el) => {this.outputEnd = el }}></span></Feed.Event>
      </Feed>
    )
  }
}
