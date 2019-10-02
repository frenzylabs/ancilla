//
//  list.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React        from 'react'
import TextTruncate from 'react-text-truncate'
import {connect}    from 'react-redux'

import {
  Menu,
  Header,
  Button,
  Icon
} from 'semantic-ui-react'

import NewConnectionModal from './new/modal'

class ConnectionList extends React.Component {
  constructor(props) {
    super(props)

    this.renderList = this.renderList.bind(this)
  }

  renderList() {
    if(this.props.printers.length < 1) {
      return (
        <Menu.Item key="-1" disabled>
          <TextTruncate line={1} truncateText="…" text="No connections." />
        </Menu.Item>
      )
    }

    return this.props.printers.map((item) => {
      return (
        <Menu.Item key={item.id} data-port-id={item.id} link>
          <TextTruncate line={1} truncateText="…" text={item.name} />
        </Menu.Item>
      )
    })
  }

  render() {
    return (
      <Menu.Item>
        <NewConnectionModal />
        Connections

        <Menu.Menu>
          {this.renderList()}
        </Menu.Menu>
      </Menu.Item>
    )
  }
}

const mapStateToProps = (state) => {
  return {
    printers: state.printer.printers
  }
}

export default connect(mapStateToProps)(ConnectionList)

