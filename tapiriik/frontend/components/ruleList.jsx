import React from 'react'
import RuleLine from './ruleLine'

export default class RuleList extends React.Component {
    render() {
        var ruleLines = this.props.data.map(function (rule) {
            return (
                <RuleLine key={rule.key} data={rule}>
                    {rule.text}
                </RuleLine>
            );
        }.bind(this));
        return (
            <div className="RuleList">
                {ruleLines}
            </div>
        );
    }
}