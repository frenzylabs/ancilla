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
            <p style={{padding: '4px 10px'}}>{item.replace("echo:", "") || "No output"}</p>
          </Feed.Summary>
        </Feed.Content>
      </Feed.Event>
    )
  }

  renderLines() {
    let output = (this.props.buffer || [])
    .map((item) => {
      return JSON.parse(item)
    })
    .filter((item) => {
      return Object.keys(item).includes('response')
    })
    .map((item) => {
      return item['response']
      .replace('\n', '')
      .replace('echo:', '')
    })
    .filter((item) => {
      return item.length > 0 && item != "start"
    })

    return output.map((line, idx) => {
      return this.renderLineItem(line, `output-line-${idx}`)
    })
  }

  render() {
    return (
      <Feed>
        <Feed.Event>&nbsp;</Feed.Event>
        {this.renderLines()}
        <Feed.Event><span ref={(el) => {this.outputEnd = el }}>&nbsp;</span></Feed.Event>
      </Feed>
    )
  }
}
