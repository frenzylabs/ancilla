//
//  body.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React, {useEffect, useRef} from 'react'

import { 
  Table
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
    return(
      <Table.Row key={index}>
        <Table.Cell colSpan={3} style={{paddingLeft: '8px'}}>
          {item.replace("echo:", "") || "No output"}
        </Table.Cell>
      </Table.Row>
    )
  }

  renderLines() {
    return (this.props.buffer || []).map((line, idx) => {
      return this.renderLineItem(line, `output-line-${idx}`)
    })
  }

  render() {
    return(
      <Table.Body>
        {this.renderLines()}
        <tr>
          <td ref={(el) => { this.outputEnd = el }}></td>
        </tr>
      </Table.Body>
    )
  }
}
