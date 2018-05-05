import React from 'react'
import ReactDOM from 'react-dom'

class AerobiaConfig extends React.Component {
    render() {
        return (
            <div>
                <p>Config asd!</p>
                df
            </div>
        );
    }
}

ReactDOM.render(
    React.createElement(AerobiaConfig, window.props),
    window.react_mount,
)