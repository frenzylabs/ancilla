//
//  form.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React from 'react'

import {
  Form,
  Button,
  Segment,
  Message,
  Icon
} from 'semantic-ui-react'

export default class ConnectionForm extends React.Component {
  constructor(props) {
    super(props)

    this.state = {
      name: null,
      port: null,
      ports: ['/some/port/here'],
      baudrates: ['115200'],
      baudrate: 115200,
      hasError: false,
      isSaving: false
    }

    this.renderSpinner    = this.renderSpinner.bind(this)
    this.portOptions      = this.portOptions.bind(this)
    this.baudrateOptions  = this.baudrateOptions.bind(this)
    this.cancelAction     = this.cancelAction.bind(this)
  }

  cancelAction(e) {
    if(e) { 
      e.preventDefault() 
    }

    if(this.props.closeAction) {
      this.props.closeAction()
    }
  }

  portOptions() {
    return (this.state.ports || []).map((port, idx) => { 
      return {
        key:    `${port}-${idx + 1}`, 
        value:  port, 
        text:   port
      } 
    })
  }

  baudrateOptions() {
    return (this.props.baudrates || []).map((rate, idx) => {
      return {
        key:    `RATE-${rate}-${idx + 1}`,
        value:  rate,
        text:   rate
      }
    })
  }

  renderSpinner() {
    return(
      <Message icon>
      <Icon name='circle notched' loading />
      <Message.Content>
        Saving port.
      </Message.Content>
    </Message>
    );
  }

  render() {
    if(this.state.isSaving) {
      return this.renderSpinner()
    }

    return (
      <Form error>
        <Segment.Group>
          <Segment>
            {this.state.hasError && (
              <Message error content='A name and port is required'/>
            )}

            <Form.Field>
              <label>Name</label>
              <input id="conn_name" placeholder="Connection name" defaultValue={this.state.port}/>
            </Form.Field>

            <Form.Field>
              <Form.Select
                fluid
                label="Port"
                options={this.portOptions()}
                placeholder='Select Port'
              />
            </Form.Field>

            <Form.Field>
              <Form.Select
                fluid
                label="Baudrate"
                options={this.baudrateOptions()}
                placeholder='Select Baudrate'
                defaultValue={this.state.baudrate}
                onChange={this.baudrateAction}
              />
            </Form.Field>
          </Segment>

          <Segment textAlign='right'>
            <Button basic onClick={this.cancelAction}>Cancel</Button>
            <Button type='submit' color='green'>Save</Button>
          </Segment>
        </Segment.Group>
      </Form>
    )
  }
}
