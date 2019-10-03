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

import $ from 'jquery/dist/jquery'

import {
  Menu,
  Header,
  Button,
  Icon
} from 'semantic-ui-react'

import {default as actions}            from '../../store/actions/connection'
import NewConnectionModal from './new/modal'

class ConnectionList extends React.Component {
  constructor(props) {
    super(props)

    this.connectionSelect = this.connectionSelect.bind(this)
    this.renderList       = this.renderList.bind(this)
  }

  connectionSelect(e) {
    e.preventDefault()
    
    let target    = $(e.currentTarget)
    let name      = target.attr('data-name')
    let path      = target.attr('data-port')
    let baudrate  = target.attr('data-baudrate')

    this.props.dispatch(
      actions.connect(name, 5000, path, baudrate)
    )
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
        <Menu.Item key={item.id} id={`port-${item.id}`} data-name={item.name} data-port={item.port} data-baudrate={item.baud_rate} link onClick={this.connectionSelect}>
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

