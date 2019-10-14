//
//  modal.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React from 'react'
import {connect}    from 'react-redux'

import {
  Icon,
  Modal,
  Button
} from 'semantic-ui-react'

import ConnectionForm from './form'

class NewConnectionModal extends React.Component {
  constructor(props) {
    super(props)

    this.state = {
      opened: false
    }

    this.handleClose    = this.handleClose.bind(this)
    this.handleOpen     = this.handleOpen.bind(this)
    this.renderTrigger  = this.renderTrigger.bind(this)
  }

  handleClose() {
    this.setState({opened: false})
  }

  handleOpen() {
    this.setState({opened: true})
  }

  renderTrigger() {
    return (
      <Icon
        link
        name="add"
        onClick={this.handleOpen}
      />
    )
  }

  render() {
    return (
      <Modal size='tiny' centered={false} trigger={this.renderTrigger()} open={this.state.opened} onClose={this.handleClose}>
        <Modal.Header>
          Add a New Connection
        </Modal.Header>

        <Modal.Content>
          <ConnectionForm closeAction={this.handleClose}/>
        </Modal.Content>
      </Modal>
    )
  }
}

const mapStateToProps = (state) => {
  return {
    error: state.printer.error
  }
}

export default connect(mapStateToProps)(NewConnectionModal)
